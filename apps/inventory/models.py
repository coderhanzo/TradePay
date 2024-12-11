import datetime
from django.db import models
from mptt.models import MPTTModel, TreeForeignKey, TreeManyToManyField
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator, MinValueValidator
from autoslug import AutoSlugField
from apps.profiles.models import Company
from django_countries.fields import CountryField
from django.utils.timezone import localdate, now
from datetime import timedelta
import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from multiselectfield import MultiSelectField
import uuid

# Create your models here.

class TimeStampedUUIDModel(models.Model):
    pkid = models.BigAutoField(primary_key=True, editable=False)
    id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Category(MPTTModel):
    """
    Inventory Category table implemented with MPTT
    """

    name = models.CharField(
        max_length=100,
        help_text=_("format: required, max-100"),
        unique=True,
    )
    slug = AutoSlugField(
        populate_from="name",
        unique=True,
    )
    is_active = models.BooleanField(
        default=True,
    )

    parent = TreeForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="children",
        null=True,
        blank=True,
        unique=False,
        verbose_name=_("parent of category"),
        help_text=_("format: not required"),
    )
    companies = models.ManyToManyField(Company, blank=True, related_name="categories")

    description = models.TextField(blank=True, null=True)

    def user_directory_path(instance, filename):
        # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
        return "{0}/{1}".format("categories", filename)

    category_image = models.FileField(
        upload_to=user_directory_path, blank=True, null=True
    )

    class MPTTMeta:
        order_insertion_by = ["name"]

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return str(self.name) if self.name else ""


class ProductDocument(models.Model):
    def user_directory_path(instance, filename):
        # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
        filename = instance.name if instance.name else filename
        return "user_{0}/{1}".format("main", filename)

    name = models.CharField(
        verbose_name=_("File Name"), blank=True, null=True, max_length=500
    )
    file = models.FileField(upload_to=user_directory_path, blank=True, null=True)
    date_uploaded = models.DateTimeField(auto_now_add=True, blank=True, null=True)


class ProductImage(models.Model):
    def user_directory_path(instance, filename):
        # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
        return "user_{0}/{1}".format("main", filename)

    image = models.FileField(upload_to=user_directory_path, blank=True, null=True)


class Product(models.Model):
    """
    Product details table
    """

    CERTIFICATE_TYPE = (
        ("BRC", _("BRC Standard")),
        ("COSMOS", _("COSMOS Organic and Natural")),
        ("CFC", _("Cruelty Free Certificate")),
        ("EnergyStar", _("Energy Star")),
        ("FairTradeCertificate", _("Fair Trade Certificate")),
        ("FCC", _("FCC Certificate")),
        ("FSC", _("FSC Certificate")),
        ("GOTS", _("GOTS Certificcate")),
        ("HACCP", _("HACCP")),
        ("HALAL", _("HALAL Certificate")),
        ("ISO9001", _("ISO 9001")),
        ("ISO14001", _("ISO 14001")),
        ("ISO22000", _("ISO 22000")),
        ("ISO_TS", _("ISO_TS 16949")),
        ("Kosher", _("Kosher")),
        ("Non-GMO", _("Non-GMO Certificate")),
        ("RoHS", _("RoHS Compliance")),
        ("Wrap", _("Wrap Certificate")),
        ("Other", _("Other")),
    )

    TIME_SPAN = (
        ("Weekly", _("Weekly")),
        ("Monthly", _("Monthly")),
        ("Quarterly", _("Quarterly")),
        ("Bi-Yearly", _("Bi-Yearly")),
        ("Yearly", _("Yearly")),
    )

    MEASURE_UNIT = (
        ("Kilogram", _("Kilogram")),
        ("Litre", _("Litre")),
        ("Pack", _("Pack")),
        ("Set", _("Set")),
        ("Ton", _("Ton")),
    )

    SHIPPING_INFORMATION = (
        ("ESX", _("ESX")),
        ("FCA", _("FCA")),
        ("FAS", _("FAS")),
        ("FOB", _("FOB")),
        ("CFR/CIF", _("CFR/CIF")),
        ("DPU", _("DPU")),
        ("DPA", _("DPA")),
        ("DDP", _("DDP")),
    )

    TRADING_AREAS = (
        ("Domestic", _("Domestic")),
        ("International", _("International")),
    )

    PAYMENT_METHODS = (
        ("papss", _("PAPSS")),
        ("peoples_pay", _("Peoples Pay")),
        ("letter_of_credit", _("Letter of Credit")),
        ("cash_against_document", _("Cash Against Document")),
    )

    name = models.CharField(
        max_length=255,
        verbose_name=_("product name"),
        help_text=_("format: required, max-255"),
    )
    seller = models.ForeignKey(
        Company,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="products",
    )
    slug = AutoSlugField(populate_from="name", unique=True)
    sku = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(
        unique=False,
        null=False,
        blank=False,
        verbose_name=_("product description"),
        help_text=_("format: required"),
    )
    categories = TreeManyToManyField(Category, blank=True, related_name="products")
    is_active = models.BooleanField(
        unique=False,
        null=False,
        blank=False,
        default=True,
        verbose_name=_("product visibility"),
        help_text=_("format: true=product visible"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        verbose_name=_("date product last created"),
        help_text=_("format: Y-m-d H:M:S"),
    )
    updated_at = models.DateTimeField(
        auto_now_add=True,
        editable=False,
        verbose_name=_("date product last updated"),
        help_text=_("format: Y-m-d H:M:S"),
    )

    def user_directory_path(instance, filename):
        # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
        return "user_{0}/{1}".format("main", filename)

    brochure = models.FileField(upload_to=user_directory_path, blank=True, null=True)
    images = models.ManyToManyField(ProductImage, blank=True, related_name="product")
    documents = models.ManyToManyField(
        ProductDocument, blank=True, related_name="product"
    )
    views = models.IntegerField(default=0)
    unit = models.CharField(max_length=250, blank=True, null=True)
    weight = models.CharField(max_length=20, blank=True, null=True)
    cost = models.DecimalField(decimal_places=2, default="0.00", max_digits=20)
    """
All fields with MultiSelectField will be saved as a comma separated string,
add "max_choices" to limit the number of choices for the radio buttons
"""
    cert = models.CharField(
        choices=CERTIFICATE_TYPE,
        blank=True,
        null=True,
        max_length=250,
        verbose_name=_("Certification Type"),
    )
    cert_number = models.IntegerField(default=0, verbose_name=_("Certification Number"))
    organization = models.CharField(max_length=250, blank=True, null=True)
    issue_date = models.DateField(help_text=_("format: Y-m-d"), blank=True, null=True)
    date_valid = models.DateField(help_text=_("format: Y-m-d"), blank=True, null=True)
    product_cap = models.CharField(
        max_length=250, blank=True, null=True, verbose_name=_("Product Capacity")
    )
    # unit = models.ForeignKey(SampleInformation, on_delete=models.CASCADE, blank=True, null=True)
    time_span = models.CharField(
        choices=TIME_SPAN,
        max_length=250,
        verbose_name=_("Time Span"),
        blank=True,
        null=True,
    )
    brand_name = models.CharField(
        max_length=250, blank=True, null=True, verbose_name=_("Brand Name")
    )
    order_quantity = models.CharField(
        max_length=250, verbose_name=_("Maximum Order Quantity"), blank=True, null=True
    )
    order_unit = models.CharField(
        choices=MEASURE_UNIT,
        max_length=250,
        verbose_name=_("Measure"),
        blank=True,
        null=True,
    )
    sample_price = models.DecimalField(
        decimal_places=2,
        default="0.00",
        max_digits=20,
        verbose_name=_("Sample Price"),
        blank=True,
        null=True,
    )
    brand_name = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        verbose_name=_("Brand Name"),
    )

    payment_methods = MultiSelectField(
        choices=PAYMENT_METHODS,
        max_choices=3,
        max_length=250,
        verbose_name=_("Payment Methods"),
        blank=True,
        null=True,
    )
    trading_areas = models.CharField(
        choices=TRADING_AREAS,
        max_length=250,
        verbose_name=_("Trading Areas"),
        blank=True,
        null=True,
    )
    shipping_information = MultiSelectField(
        choices=SHIPPING_INFORMATION,
        max_choices=3,
        max_length=250,
        verbose_name=_("Shipping Information"),
        blank=True,
        null=True,
    )

    def __str__(self):
        return str(self.name) if self.name else ""


# class CurrencyRates(models.Model):
#     currency_rate_timestamp = models.DateTimeField()
#     ghs = models.FloatField(default=1.0, blank=True, null=True)
#     tzs = models.FloatField(default=1.0, blank=True, null=True)
#     xof = models.FloatField(default=1.0, blank=True, null=True)
#     xaf = models.FloatField(default=1.0, blank=True, null=True)
#     ngn = models.FloatField(default=1.0, blank=True, null=True)
#     eur = models.FloatField(default=1.0, blank=True, null=True)
#     usd = models.FloatField(default=1.0, blank=True, null=True)

#     @property
#     def rates(self):
#         if self.currency_rate_timestamp + timedelta(hours=1) < now():
#             try:
#                 response = requests.get(
#                     "http://api.exchangeratesapi.io/v1/latest",
#                     params={
#                         "access_key": settings.EXCHANGE_RATE_API_KEY,
#                         "symbols": "GHS,XOF,TZS,NGN,USD,LRD,GMD,CVE,GNF,MRU,XAF,CDF,AOA,RWF,BIF,STN,ZAR,NAD,BWP,KES",
#                     },
#                 )
#                 data = response.json()
#                 if data.get("success"):
#                     self.ghs = data["rates"].get("GHS", self.ghs)
#                     self.tzs = data["rates"].get("TZS", self.tzs)
#                     self.xof = data["rates"].get("XOF", self.xof)
#                     self.ngn = data["rates"].get("NGN", self.ngn)
#                     self.xaf = data["rates"].get("XAF", self.xaf)
#                     self.eur = data["rates"].get("EUR", self.eur)
#                     self.usd = data["rates"].get("USD", self.usd)
#                     self.currency_rate_timestamp = now()
#                     self.save()
#                     return data["rates"]
#             except requests.RequestException as e:
#                 # Handle request exceptions (e.g., network issues)
#                 pass
#         return {
#             "GHS": self.ghs,
#             "TZS": self.tzs,
#             "XOF": self.xof,
#             "NGN": self.ngn,
#             "XAF": self.xaf,
#             "EUR": self.eur,
#             "USD": self.usd,
#         }

#     def save(self, *args, **kwargs):
#         if not self.pk and CurrencyRates.objects.exists():
#             # If you're trying to create a new instance and one already exists
#             raise ValidationError("There is can be only one CurrentRates instance")
#         return super(CurrencyRates, self).save(*args, **kwargs)


class ProductViews(TimeStampedUUIDModel):
    ip = models.CharField(verbose_name=_("IP Address"), max_length=250)
    product = models.ForeignKey(
        Product, related_name="product_views", on_delete=models.CASCADE
    )

    def __str__(self):
        return f"Total views on - {self.product.name} is - {self.product.views} view(s)"

    class Meta:
        verbose_name = "Total Views on Product"
        verbose_name_plural = "Total Product Views"


class SourcingRequest(models.Model):
    name = models.CharField(
        verbose_name=_("Product Name"), max_length=50, blank=True, null=True
    )
    category = models.OneToOneField(
        Category,
        verbose_name=_("Product Category"),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    quantity = models.TextField(
        verbose_name=_("Fill in Sourcing Requirements"),
        blank=True,
        null=True,
        max_length=500,
    )
    terms_of_delivery = models.CharField(
        verbose_name=_("Terms of Delivery"), max_length=50, blank=True, null=True
    )
    delivery_location = CountryField(
        verbose_name=_("Delivery Country"), default="PL", blank=True
    )
    required_amount = models.DecimalField(
        decimal_places=2,
        default="0.00",
        max_digits=20,
        verbose_name=_("Required Amount"),
        blank=True,
        null=True,
    )
    unit = models.CharField(max_length=250, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.name) if self.name else ""


def current_year():
    return datetime.date.today().year


class QuotationImage(models.Model):
    def user_directory_path(instance, filename):
        # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
        return "user_{0}/{1}".format("main", filename)

    image = models.FileField(upload_to=user_directory_path, blank=True, null=True)


class QuotationForm(models.Model):
    name = models.CharField(
        verbose_name=_("Product Name"), max_length=250, blank=True, null=True
    )
    YEAR_CHOICES = [(r, r) for r in range(1984, current_year() + 1)]
    year = models.IntegerField(
        verbose_name=_("Production Year"),
        validators=[MinValueValidator(2000), MaxValueValidator(current_year())],
        choices=YEAR_CHOICES,
        default=current_year,
    )
    specs = models.TextField(
        verbose_name=_("Product Specifications"), max_length=250, blank=True, null=True
    )
    message = models.TextField(
        verbose_name=_("Message To Buyer"), max_length=500, blank=True, null=True
    )
    price = models.DecimalField(
        decimal_places=2,
        default="0.00",
        max_digits=20,
        verbose_name=_("Price Offer"),
        blank=True,
        null=True,
    )
    unit = models.CharField(max_length=250, blank=True, null=True)

    def user_directory_path(instance, filename):
        # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
        return "user_{0}/{1}".format("main", filename)

    quotation_image = models.FileField(
        upload_to=user_directory_path,
        blank=True,
        null=True,
        verbose_name="Upload pictures of product",
    )

    def __str__(self):
        return str(self.name) if self.name else ""
