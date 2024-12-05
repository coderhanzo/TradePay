from django.shortcuts import render
from rest_framework import generics, filters, status, permissions
from rest_framework.decorators import (
    api_view,
    permission_classes,
    authentication_classes,
)
from .serializers import (
    ProductReturnSerializer,
    ProductCreateSerializer,
    CategorySerializer,
    ProductImageSerializer,
    CurrencyRatesSerializer,
    ProductDocumentSerializer,
    CategoryReturnSerializer,
    SourcingRequestSerializer,
    QuotationImageSerializer,
    QuotationSerializer,
)
from copy import deepcopy
from .models import (
    Product,
    Category,
    CurrencyRates,
    Company,
    ProductViews,
    SourcingRequest,
    QuotationForm,
)
from apps.profiles.models import ContactPerson
from rest_framework.response import Response
from django.db import transaction, IntegrityError
from rest_framework.views import APIView
from django.utils.timezone import now
from datetime import timedelta
from django.db.models import Count
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import AllowAny

# Create your views here.

from utils.fuzzysearch import FuzzySearchFilter

User = get_user_model()


class SearchProduct(generics.ListAPIView):
    """
    Fuzzy Search allows for typos, but the tradeoff is speed,
    increasing fuzz ratio in utils.fuzzysearch will yield faster results,
    and decreasing will yield slower results but allows for greater margin
    or error when searching
    """

    serializer_class = ProductReturnSerializer
    filter_backends = [
        FuzzySearchFilter,
    ]
    search_fields = ["name", "description"]

    def get_queryset(self):
        # if superuser queryset equals all, if not qs equals is_active=True
        if self.request.user.is_staff or self.request.user.is_superuser:
            queryset = Product.objects.filter().order_by("-updated_at")
        else:
            queryset = Product.objects.filter(is_active=True).order_by("-updated_at")
        product_id = self.request.query_params.get("id")
        company_id = self.request.query_params.get("company_id")
        category = self.request.query_params.get("category")
        top = self.request.query_params.get("top")
        limit = self.request.query_params.get("limit")
        if product_id:
            product = Product.objects.filter(id=product_id).order_by("-updated_at")
            if len(product) > 0:
                # Update views and prevent spam views
                x_forwarded_for = self.request.META.get("HTTP_X_FORWARDED_FOR")
                if x_forwarded_for:
                    ip = x_forwarded_for.split(",")[0]
                else:
                    ip = self.request.META.get("REMOTE_ADDR")

                if not ProductViews.objects.filter(product=product[0], ip=ip).exists():
                    ProductViews.objects.create(product=product[0], ip=ip)

                    product[0].views += 1
                    product[0].save()

            queryset = product
        elif company_id:
            queryset = Product.objects.filter(
                seller=company_id, is_active=True
            ).order_by("-updated_at")
        elif top:
            queryset = Product.objects.filter(is_active=True).order_by("-views")[:4]
        elif limit:
            queryset = queryset[: int(limit)]
        elif category:
            queryset = (
                Product.objects.filter(categories__name=category, is_active=True)
                .order_by("-updated_at")
                .distinct()
            )
        return queryset


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
@authentication_classes([JWTAuthentication])
def get_my_products(request):
    user_instance = User.objects.filter(id=request.user.id)
    products = []
    if user_instance[0].admin_profile:
        for company in user_instance[0].admin_profile.companies.all():
            products.extend(
                ProductReturnSerializer(instance=company.products.all(), many=True).data
            )
    else:
        return Response("Must be an admin", status=status.HTTP_401_UNAUTHORIZED)
    return Response(products, status=status.HTTP_200_OK)


@api_view(["GET"])
def get_number_of_products(request):
    return Response(
        {"uploaded_products": len(Product.objects.all())}, status=status.HTTP_200_OK
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@authentication_classes([JWTAuthentication])
@transaction.atomic
def create_product(request):
    data = request.data

    # temporarily here for dev or maybe not? If a contact person has many companies then they
    # need to explicitly state which company to add this product to
    seller_name = data["seller"]
    company_query = Company.objects.filter(company_name=seller_name)
    if len(company_query) == 1:
        company_instance = company_query[0]
        data["seller"] = company_instance.id
    else:
        # For dev this is fine, in prod this should throw an Error that the company
        # does not exist
        data.pop("seller")

    categories = []

    if "categories" in data:
        categories = data["categories"]
    category_instances = []
    # requiring a product to have categories, better error handling should be here
    for category in categories:
        try:
            category_instance = Category.objects.get(name=category)
            category_instances.append(category_instance.id)
        except Category.DoesNotExist:
            category_data = {"name": category}
            category_serializer = CategorySerializer(data=category_data)
            category_serializer.is_valid(raise_exception=True)
            category_instance = category_serializer.save()
            category_instances.append(category_instance.id)

    data["categories"] = category_instances

    image_instances = []
    if "images" in data:
        images = data["images"]
        for image in images:
            image_data = {"image": image}
            image_serializer = ProductImageSerializer(data=image_data)
            image_serializer.is_valid(raise_exception=True)
            image_instance = image_serializer.save()
            image_instances.append(image_instance.id)
    data["images"] = image_instances

    document_instances = []
    if "documents" in data:
        documents = data["documents"]
        for document in documents:
            document_serializer = ProductDocumentSerializer(data=document)
            document_serializer.is_valid(raise_exception=True)
            document_instance = document_serializer.save()
            document_instances.append(document_instance.id)
    data["documents"] = document_instances

    serializer = ProductCreateSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    product_instance = serializer.save()

    return_serializer = ProductReturnSerializer(instance=product_instance)

    return Response(return_serializer.data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@permission_classes([permissions.IsAuthenticated])
@authentication_classes([JWTAuthentication])
@transaction.atomic
def edit_product(request):
    print(request.user.is_superuser)
    data = request.data
    product_id = request.query_params.get("id")
    try:
        product_instance = Product.objects.get(id=product_id)
        contact_person = ContactPerson.objects.get(user=request.user.id) or request.user
    except Product.DoesNotExist:
        return Response(
            {"error": "No product", "status": "failed", "message": "no product"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if (product_instance.seller not in contact_person.companies.all()) and (
        not request.user.is_superuser
    ):
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    # Category must already be in the database
    if "categories" in data:
        categories = data["categories"]
        category_instances = [
            Category.objects.get(name=category).id for category in categories
        ]
        to_remove = product_instance.categories.first()
        if to_remove:
            product_instance.categories.remove(to_remove)
        for category in category_instances:
            product_instance.categories.add(category)
        product_instance.save()
        data.pop("categories")
    if "add_categories" in data:
        categories = data["add_categories"]
        category_instances = [
            Category.objects.get(name=category).id for category in categories
        ]
        for category in category_instances:
            product_instance.categories.add(category)
        product_instance.save()
        # add_categories is not a field in Product so best to remove it from data to be sent to Product
        data.pop("add_categories")
    if "remove_categories" in data:
        categories = data["remove_categories"]
        category_instances = []
        for category in categories:
            try:
                to_add = Category.objects.get(name=category).id
            except:
                return Response(status=status.HTTP_400_BAD_REQUEST)
        category_instances.append(to_add)

        for category in category_instances:
            product_instance.categories.remove(category)
        product_instance.save()
        # remove_categories is not a field in Product so best to remove it from data to be sent to Product
        data.pop("remove_categories")
    # Product Document is many to many to Product, so serilize and then add to Product
    if "add_documents" in data:
        documents = data["add_documents"]
        for document in documents:
            document_serializer = ProductDocumentSerializer(data=document)
            document_serializer.is_valid(raise_exception=True)
            document_instance = document_serializer.save()
            product_instance.documents.add(document_instance.id)
        product_instance.save()
        # add_documents is not a field in Product so best to remove it from data to be sent to Product
        data.pop("add_documents")
    if "delete_documents" in data:
        # documents are not actually deleted, but set to inactive, users should then
        # have the option to grab from trash within a period of time
        documents = data["delete_documents"]

    product_serializer = ProductReturnSerializer(instance=product_instance, data=data, partial=True)
    product_serializer.is_valid(raise_exception=True)
    product_serializer.save()

    return Response(product_serializer.data, status=status.HTTP_200_OK)


@api_view(["PATCH"])
def disable_product(request):
    product_id = request.query_params.get("id")
    product_instance = Product.objects.filter(id=product_id)
    print(product_instance)
    if len(product_instance):
        product_instance[0].is_active = False
        product_instance[0].save()
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    return Response({"success": "product disabled"}, status=status.HTTP_200_OK)


@api_view(["PATCH"])
def enable_product(request):
    product_id = request.query_params.get("id")
    product_instance = Product.objects.filter(id=product_id)
    print(product_instance)
    if len(product_instance):
        product_instance[0].is_active = True
        product_instance[0].save()
    else:
        return Response(status=status.HTTP_400_BAD_REQUEST)
    return Response({"success": "product enabled"}, status=status.HTTP_200_OK)


class SearchCategories(generics.ListAPIView):
    serializer_class = CategoryReturnSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ["name"]

    def get_queryset(self):
        queryset = Category.objects.all()
        top = self.request.query_params.get("top")
        cat_id = self.request.query_params.get("id")
        if top:
            queryset = Category.objects.annotate(
                num_products=Count("products")
            ).order_by("-num_products")[:4]
        elif cat_id:
            queryset = Category.objects.filter(id=cat_id)
        return queryset


class CreateCategory(APIView):
    @transaction.atomic
    def post(self, request):
        data = request.data
        if "parent" in data:
            try:
                parent_instance = Category.objects.get(name=data["parent"])
                data.pop("parent")
                serializer = CategorySerializer(data=data)
                serializer.is_valid(raise_exception=True)
                category = serializer.save()
                category.parent = parent_instance
                category.save()
            except Category.DoesNotExist:
                custom_response_data = {
                    # customize your response format here
                    "errors": "Category not found",
                    "status": "failed",
                    "message": "Category of the name requested as parent category does not exist",
                }
                return Response(
                    custom_response_data, status=status.HTTP_400_BAD_REQUEST
                )
        else:
            serializer = CategorySerializer(data=data)
            serializer.is_valid(raise_exception=True)
            category = serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["PATCH"])
@transaction.atomic
def edit_category(request):
    data = request.data
    category_id = request.query_params.get("id")
    try:
        if category_id:
            category_instance = Category.objects.get(id=category_id)
        else:
            category_instance = Category.objects.get(name=data["name"])
    except Category.DoesNotExist:
        custom_response_data = {
            # customize your response format here
            "errors": "Category not found",
            "status": "failed",
            "message": "Category of the name requested as parent category does not exist",
        }
        return Response(custom_response_data, status=status.HTTP_400_BAD_REQUEST)
    serializer = CategorySerializer(instance=category_instance, partial=True, data=data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@transaction.atomic
def get_currency_rates(request):
    rates = None
    data = request.data
    try:
        rates = CurrencyRates.objects.get()
    except CurrencyRates.DoesNotExist:
        data["currency_rate_timestamp"] = now() - timedelta(hours=3)
        serializer = CurrencyRatesSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        rates = serializer.save()

    serializer = CurrencyRatesSerializer(rates)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([permissions.IsAdminUser])
@authentication_classes([JWTAuthentication])
def get_all_products(request):
    serializer = ProductReturnSerializer(data=Product.objects.all(), many=True)
    serializer.is_valid()
    return Response({"all_products": serializer.data}, status=status.HTTP_200_OK)



class SourcingRequestListCreateView(generics.ListCreateAPIView):
    serializer_class = SourcingRequestSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = SourcingRequest.objects.all()
        category_id = self.request.query_params.get("category", None)
        if category_id is not None:
            queryset = queryset.filter(category__id=category_id)
        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)



class SourcingRequestDeleteView(generics.DestroyAPIView):
    queryset = SourcingRequest.objects.all()
    serializer_class = SourcingRequestSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        if self.request.user.is_staff:
            return SourcingRequest.objects.all()
        else:
            return SourcingRequest.objects.filter(user=self.request.user)


@api_view(["POST"])
@permission_classes([AllowAny])
@transaction.atomic
def create_quotation(request):
    quotation_data = deepcopy(request.data)  # Create a mutable copy
    image_ids = []

    if "images" in quotation_data:
        for image in quotation_data.pop("images"):
            image_data = {"image": image}
            image_serializer = QuotationImageSerializer(data=image_data)
            image_serializer.is_valid(raise_exception=True)
            image_instance = image_serializer.save()
            image_ids.append(image_instance.id)

    quotation_data["images"] = image_ids

    quotation_serializer = QuotationSerializer(data=quotation_data)
    quotation_serializer.is_valid(raise_exception=True)
    quotation_serializer.save()

    return Response(quotation_serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
def get_quotations(request):
    quotation_id = request.query_params.get("id")  # Get the `id` parameter from the query string
    
    if quotation_id:
        try:
            # Fetch a single quotation by ID
            quotation_data = QuotationForm.objects.get(id=quotation_id)
            serializer = QuotationSerializer(quotation_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except QuotationForm.DoesNotExist:
            return Response({"detail": "Quotation not found."}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Fetch all quotations
        quotation_data = QuotationForm.objects.all()
        serializer = QuotationSerializer(quotation_data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)