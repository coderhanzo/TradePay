from rest_framework import serializers
from .models import (
    Product,
    Category,
    ProductImage,
    CurrencyRates,
    ProductDocument,
    SourcingRequest,
    QuotationForm,
    QuotationImage,
)
from utils.utils import Base64File
import base64


class CurrencyRatesSerializer(serializers.ModelSerializer):
    rates = serializers.SerializerMethodField()

    class Meta:
        model = CurrencyRates
        fields = "__all__"

    def get_rates(self, obj):
        return obj.rates


class ProductReturnSerializer(serializers.ModelSerializer):
    categories = serializers.SerializerMethodField(required=False)
    images = serializers.SerializerMethodField(required=False)
    brochure = serializers.SerializerMethodField(required=False)
    seller = serializers.SerializerMethodField(required=False)
    rates = serializers.SerializerMethodField(required=False)
    documents = serializers.SerializerMethodField(required=False)
    about_company = serializers.SerializerMethodField(required=False)

    class Meta:
        model = Product
        fields = "__all__"

    def get_seller(self, obj):
        return obj.seller.company_name if obj.seller else ""

    def get_about_company(self, obj):
        return obj.seller.about if obj.seller else ""

    def get_categories(self, obj):
        return [category.name for category in obj.categories.all()]

    def get_images(self, obj):
        return [
            "https://www.tradepayafrica.com" + pic.image.url for pic in obj.images.all()
        ]
        # images_data = []
        # for pic in obj.images.all():
        #     try:
        #         # Open the file in binary mode ('rb')
        #         with pic.image.open("rb") as file:
        #             # Read the file content and encode it in Base64
        #             encoded_image = base64.b64encode(file.read())
        #             # Decode the Base64 encoded bytes to string
        #             images_data.append(encoded_image.decode("utf-8"))
        #     except IOError:
        #         # Handle file not found, etc.
        #         continue
        # return images_data

    def get_brochure(self, obj):
        return (
            "https://www.tradepayafrica.com" + obj.brochure.url if obj.brochure else ""
        )

    def get_documents(self, obj):
        return [
            {
                "filename": document.name,
                "file": "https://www.tradepayafrica.com" + document.file.url,
                "date_uploaded": (
                    document.date_uploaded if document.date_uploaded else ""
                ),
            }
            for document in obj.documents.all()
        ]

    # Not fully stable, shouldn't be a problem though if database is backed up
    # Could wrap get in a try catch, and then make a call to get currency endpoint, to make stable
    def get_rates(self, obj):
        currency_instance = CurrencyRates.objects.get()
        serializer = CurrencyRatesSerializer(instance=currency_instance)
        data = serializer.data
        data.pop("rates")
        data.pop("currency_rate_timestamp")
        return data


class ProductCreateSerializer(serializers.ModelSerializer):
    categories = serializers.PrimaryKeyRelatedField(
        required=False, many=True, queryset=Category.objects.all()
    )
    brochure = Base64File(required=False)

    # Payments
    papss = serializers.SerializerMethodField()
    peoples_pay = serializers.SerializerMethodField()
    letter_of_credit = serializers.SerializerMethodField()
    cash_against_document = serializers.SerializerMethodField()

    # Shipping information
    esx = serializers.SerializerMethodField()
    fca = serializers.SerializerMethodField()
    fas = serializers.SerializerMethodField()
    fob = serializers.SerializerMethodField()
    cfr_cif = serializers.SerializerMethodField()
    dpu = serializers.SerializerMethodField()
    dpa = serializers.SerializerMethodField()
    ddp = serializers.SerializerMethodField()

    # Trading areas
    domestic = serializers.SerializerMethodField()
    international = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = "__all__"

    def get_categories(self, obj):
        return [category.name for category in obj.categories.all()]

    def get_papss(self, obj):
        return "papss" in obj.payments

    def get_peoples_pay(self, obj):
        return "peoples_pay" in obj.payments

    def get_letter_of_credit(self, obj):
        return "letter_of_credit" in obj.payments

    def get_cash_against_document(self, obj):
        return "cash_against_document" in obj.payment

    # Shipping information
    def get_esx(self, obj):
        return "ESX" in obj.shipping_information

    def get_fca(self, obj):
        return "FCA" in obj.shipping_information

    def get_fas(self, obj):
        return "FAS" in obj.shipping_information

    def get_fob(self, obj):
        return "FOB" in obj.shipping_information

    def get_cfr_cif(self, obj):
        return "CFR/CIF" in obj.shipping_information

    def get_dpu(self, obj):
        return "DPU" in obj.shipping_information

    def get_dpa(self, obj):
        return "DPA" in obj.shipping_information

    def get_ddp(self, obj):
        return "DDP" in obj.shipping_information

    # Trading areas
    def get_domestic(self, obj):
        return "Domestic" in obj.trading_areas

    def get_international(self, obj):
        return "International" in obj.trading_areas


class ProductImageSerializer(serializers.ModelSerializer):
    image = Base64File()

    class Meta:
        model = ProductImage
        fields = "__all__"


class CategorySerializer(serializers.ModelSerializer):
    category_image = Base64File(required=False)

    class Meta:
        model = Category
        fields = "__all__"


class CategoryReturnSerializer(serializers.ModelSerializer):
    category_image = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = "__all__"

    def get_category_image(self, obj):
        return (
            "https://www.tradepayafrica.com" + obj.category_image.url
            if obj.category_image
            else ""
        )


class ProductDocumentSerializer(serializers.ModelSerializer):
    file = Base64File()

    class Meta:
        model = ProductDocument
        fields = "__all__"


class SourcingRequestSerializer(serializers.ModelSerializer):
    Category = serializers.PrimaryKeyRelatedField(
        many=False, queryset=Category.objects.all()
    )

    class Meta:
        model = SourcingRequest
        fields = "__all__"


class QuotationImageSerializer(serializers.ModelSerializer):
    quotation_image = Base64File()

    class Meta:
        model = QuotationImage
        fields = "__all__"


class QuotationSerializer(serializers.ModelSerializer):


    class Meta:
        model = QuotationForm
        fields = "__all__"
