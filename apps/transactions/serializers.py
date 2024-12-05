from rest_framework import serializers
from .models import Payments, Collections, CollectionsCard
from rest_framework.exceptions import ValidationError
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import os


class PaymentsSerializer(serializers.ModelSerializer):
    # operation = serializers.CharField(max_length=255, default="CREDIT")

    class Meta:
        model = Payments
        fields = "__all__"


class CollectionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Collections
        fields = [
            "transaction_id",
            "amount",
            "transaction_status",
            "account_name",
            "description",
            "account_number",
            "account_issuer",
            "callbackUrl",
        ]
        extra_kwargs = {
            "amount": {"required": True},
            "account_name": {"required": True},
            "account_number": {"required": True},
            "account_issuer": {"required": True},
        }


class NameEnquirySerializer(serializers.Serializer):
    account_type = serializers.CharField(max_length=100)
    account_number = serializers.CharField(max_length=100)
    account_issuer = serializers.CharField(max_length=100)


class CardDetailsSerializer(serializers.Serializer):
    number = serializers.CharField(max_length=16, write_only=True)
    cvc = serializers.CharField(max_length=4, write_only=True)
    expiry = serializers.CharField(max_length=7, write_only=True)


class CollectionsCardSerializer(serializers.ModelSerializer):
    card = CardDetailsSerializer(write_only=True)  # Nested serializer for card details

    class Meta:
        model = CollectionsCard
        fields = "__all__"

    def create(self, validated_data):
        # Retrieve the nested 'card' data
        card_data = validated_data.pop("card", None)
        if not card_data:
            raise serializers.ValidationError({"card": "Card details are required."})

        # Generate a new salt
        salt = os.urandom(20)

        # Hash card details
        def hash_value(value, salt):
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=20,
                salt=salt,
                iterations=100000,
                backend=default_backend(),
            )
            return kdf.derive(value.encode())  # Convert value to bytes for hashing

        # Add hashed values to validated_data
        validated_data["number"] = hash_value(card_data["number"], salt)
        validated_data["cvc"] = hash_value(card_data["cvc"], salt)
        validated_data["expiry"] = hash_value(card_data["expiry"], salt)
        validated_data["salt"] = salt

        # Create and return the instance
        return CollectionsCard.objects.create(**validated_data)
