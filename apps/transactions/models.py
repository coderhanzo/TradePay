from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.auth import get_user_model
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from hashlib import sha256
import os
import uuid


# this model will replace donations
class Payments(models.Model):
    external_transaction_id = models.UUIDField(
        default=uuid.uuid4, editable=False, primary_key=True
    )
    amount = models.CharField(max_length=100)
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=100)
    account_issuer = models.CharField(max_length=100)
    description = models.CharField(max_length=100, default="description")
    # this will be for the database, so every transaction will have an id, we can use uuid for this,
    # then we will have to call it in the view or call back url when we need to verify the payment
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # read only field that cant be changed and remains constant
    operation = models.CharField(max_length=100, default="CREDIT", editable=False)

    def __str__(self):
        return f"{self.account_name} {self.account_number} {self.created_at}"


# this model will replace WAQF donations/ projectdonations
class Collections(models.Model):
    NETWORK_TYPE_CHOICES = (
        ("MTN", "mtn"),
        ("vodafone", "vodafone"),
        ("AIRTELTIGO", "airteltigo"),
    )
    PAYMENT_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    amount = models.CharField(max_length=100)
    transaction_status = models.CharField(
        max_length=100, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )
    account_name = models.CharField(max_length=100)
    account_number = models.CharField(max_length=100)
    account_issuer = models.CharField(max_length=100)
    callbackUrl = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=50, default="transaction description")
    external_transaction_id = models.UUIDField(
        default=uuid.uuid4, editable=False, primary_key=True
    )
    transaction_id = models.CharField(
        editable=False, unique=True, max_length=255, default="peoplespay_id"
    )

    def __str__(self):
        return f"Collection: {self.amount} - {self.transaction_status} - {self.external_transaction_id}"


class CollectionsCard(models.Model):
    external_transaction_id = models.UUIDField(
        default=uuid.uuid4, editable=False, primary_key=True, unique=True
    )
    callbackUrl = models.URLField(blank=True, null=True)
    clientRedirectUrl = models.URLField(blank=True, null=True)
    account_name = models.CharField(max_length=100, default="account_name")
    description = models.CharField(max_length=50, default="transaction description")
    amount = models.CharField(max_length=60, default="amount")
    number = models.CharField(
        editable=False, max_length=500
    )  # Store as binary data after hashing
    cvc = models.CharField(editable=False, max_length=500)
    expiry = models.CharField(editable=False, max_length=500)
    salt = models.BinaryField(editable=False)  # Salt is binary data
    created_at = models.DateTimeField(auto_now_add=True)
    card_transaction_id = models.CharField(
        editable=False, unique=True, max_length=255, default="peoplespay_id"
    )

    def _hash_value(self, value, salt):
        if not isinstance(value, str):
            value = str(value)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=20,
            salt=salt,
            iterations=100000,
            backend=default_backend(),
        )

        return kdf.derive(value.encode())  # Convert value to bytes for hashing

    def __str__(self):
    # Display first 10 characters of hashed card_number in hex
        card_number_hex = self.number[:10].hex() if self.number else "N/A"
        return f"Card Info (Hashed): {card_number_hex}... with Salt"
