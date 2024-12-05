import collections
import json
from urllib import request
from django.shortcuts import render
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Payments, Collections, CollectionsCard
from .serializers import (
    PaymentsSerializer,
    CollectionsSerializer,
    CollectionsCardSerializer,
    NameEnquirySerializer,
)
from .services import PeoplesPayService
from django.urls import reverse
import requests
import uuid


class TokenView(APIView):
    def get(self, request):
        token = PeoplesPayService.get_token()

        if token:
            return Response({"token": token}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "Failed to retrieve token"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PaymentsView(APIView):
    def post(self, request):
        payment_serializer = PaymentsSerializer(data=request.data)
        # Get the token using the PeoplesPayService from the .get_token() method
        print(payment_serializer, f"payment serializer")
        token = PeoplesPayService.get_token(operation="CREDIT")
        print(token, f"token")
        if token is None:
            return Response(
                {"message": "Failed to retrieve token"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if payment_serializer.is_valid():
            validated_data = payment_serializer.validated_data
            print(validated_data, f"validated data")
        # Disburse payment
        disburse_payload = {
            "amount": str(validated_data["amount"]),
            "account_number": validated_data["account_number"],
            "account_name": validated_data["account_name"],
            "account_issuer": validated_data["account_issuer"],
            # "external_transaction_id": validated_data["external_transaction_id"],
            "description": validated_data["description"],
        }
        disburse_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token['data']}",
        }
        print(disburse_payload, f"Disburse payload")

        try:
            disburse_response = requests.post(
                f"{PeoplesPayService.BASE_URL}/disburse",
                json=disburse_payload,
                headers=disburse_headers,
            )
            disburse_data = disburse_response.json()
            print(disburse_data, f"disburse_data")

            if disburse_response.status_code == 200 and disburse_data.get("success"):
                payment_serializer.save()  # Save payment record to the database
                return Response(
                    {"message": "Payment processed successfully"},
                    status=status.HTTP_201_CREATED,
                )
            else:
                return Response(
                    {"message": disburse_data.get("message", "Payment failed")},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        except requests.exceptions.RequestException as e:
            return Response(
                {"message": f"Error processing payment: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class CollectionsView(APIView):
    def post(self, request):
        collection_serializer = CollectionsSerializer(data=request.data)
        # transaction_id = request.data.get("transactionId")

        # Generate the external_transaction_id at the start
        external_transaction_id = uuid.uuid4()
        print("take a look")

        if collection_serializer.is_valid():
            print("if passed")
            validated_data = collection_serializer.validated_data

            # Assign the external_transaction_id to the validated data after it is available
            validated_data["external_transaction_id"] = external_transaction_id

            # Get the token using the PeoplesPayService
            token = PeoplesPayService.get_token()
            print(token)
            if token is None:
                return Response(
                    {"message": "Failed to retrieve token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Process the collection
            collection_payload = {
                "amount": str(validated_data["amount"]),
                "account_number": validated_data["account_number"],
                "account_name": validated_data["account_name"],
                "account_issuer": validated_data["account_issuer"],
                "callbackUrl": validated_data["callbackUrl"],
                "description": validated_data["description"],
                "externalTransactionId": str(external_transaction_id),
            }
            collection_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token['data']}",
            }

            try:
                print(collection_payload, f"trying to send collection")
                collection_response = requests.post(
                    f"{PeoplesPayService.BASE_URL}/collectmoney",
                    json=collection_payload,
                    headers=collection_headers,
                )
                collection_data = collection_response.json()
                print(collection_data, f"collection data")

                # extract the PeoplesPay ID if available in the response
                transaction_id = collection_data.get("transactionId")

                if (
                    collection_response.status_code == 200
                    and collection_data.get("success")
                    and transaction_id
                ):
                    # Save collection record, including external_transaction_id and PeoplesPay ID
                    collection_serializer.save(
                        external_transaction_id=external_transaction_id,
                        transaction_id=transaction_id,  # Save the PeoplesPay ID
                    )
                    # Create a corresponding payment entry with the same external_transaction_id
                    Payments.objects.create(
                        external_transaction_id=external_transaction_id,
                        amount=validated_data["amount"],
                        account_name=validated_data["account_name"],
                        account_number=validated_data["account_number"],
                        account_issuer=validated_data["account_issuer"],
                    )
                    return Response(
                        {
                            "message": collection_data["message"],
                            "internal_id": str(
                                external_transaction_id
                            ),  # Internal ID for tracking
                            "peoplespay_id": collection_data[
                                "transactionId"
                            ],  # PeoplesPay ID
                            "collectin_status": collection_data["success"],
                            "collection_code": collection_data["code"],
                        },
                        status=status.HTTP_201_CREATED,
                    )

                else:
                    return Response(
                        {
                            "message": collection_data.get(
                                "message", "Collection failed"
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            except requests.exceptions.RequestException as e:
                return Response(
                    {"message": f"Error processing collection: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(
            collection_serializer.errors, status=status.HTTP_400_BAD_REQUEST
        )


# Helper function to check peoples pay for payment status
def check_peoplespay_status(transaction_id):
    url = f"{PeoplesPayService.BASE_URL}"
    print(request, f"looking at peoplespay")
    token = PeoplesPayService.get_token()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token['data']}",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get(
            "status"
        )  # Extract and return the status field from the response
    return Response({request.get("success", "code", "message")})


# Working version of callback


class PaymentCallbackAPIView(APIView):
    def post(self, request):

        # Extract PeoplesPay transaction ID and success status from the request data
        transaction_id = request.data.get("transactionId")

        payment_success = request.data.get("success")

        # incoming data from PeoplesPay for debugging
        print("Incoming request data:", json.dumps(request.data, indent=4))
        # Validate incoming data

        """
        if not transaction_id or payment_success is None:
        """
        if not transaction_id:
            return Response(
                {"error": "Missing required fields: transactionId"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Convert payment_success to a proper boolean value
        # payment_success = True if payment_success in [True, "true", "True"] else False

        # Find the collection related to this transaction using transaction_id
        """
        trying to use a for statement to get the payment status and then 
        update the status of the objects id provide
        """
        try:
            collection = Collections.objects.get(transaction_id=transaction_id)
            print(collection, f"collection data")

            # Update the transaction status based on the success value
            if payment_success:
                collection.transaction_status = "completed"
            else:
                collection.transaction_status = "failed"
            collection.save()

            # Return a response with updated information
            return Response(
                {
                    "message": request.data.get("message"),
                    "transaction_id": request.data.get("transactionId"),
                    "external_transaction_id": collection.external_transaction_id,
                    "amount": collection.amount,
                    "status": collection.transaction_status,
                    "account_name": collection.account_name,
                    "description": collection.description,
                    "created_at": collection.created_at,
                },
                status=status.HTTP_200_OK,
            )
        except Collections.DoesNotExist:
            return Response(
                {"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND
            )


class NameEnquiryView(APIView):
    def post(self, request):
        serializer = NameEnquirySerializer(data=request.data)
        token = PeoplesPayService.get_token()
        if serializer.is_valid():
            data = serializer.validated_data
            enquiry_payload = {
                "account_type": data["account_type"],
                "account_number": data["account_number"],
                "account_issuer": data["account_issuer"],
            }
            print(enquiry_payload, f"enquiry payload")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token['data']}",
            }
            print(headers, f"headers")
            try:
                response = requests.post(
                    f"{PeoplesPayService.BASE_URL}/enquiry",
                    json=enquiry_payload,
                    headers=headers,
                )
                response_data = response.json()
                print(response_data, f"response data")
                if response.status_code == 200 and response_data.get("success"):
                    return Response(
                        {
                            "message": "Enquiry processed successfully",
                            "data": response_data["data"],
                        },
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {
                            "error": response_data.get("message", "Enquiry failed"),
                            "code": response_data.get("code"),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            except requests.exceptions.RequestException as e:
                return Response(
                    {"error": f"Error processing enquiry: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CardPaymentAPIView(APIView):
    def post(self, request):
        print("Received request:", request.data)  # Debug incoming request data

        card_serializer = CollectionsCardSerializer(data=request.data)
        external_transaction_id = uuid.uuid4()

        if card_serializer.is_valid():
            print("Serializer is valid.")  # Debug serializer validation
            validated_data = card_serializer.validated_data
            print("Validated data:", validated_data)  # Debug validated data

            # Assign the external_transaction_id
            validated_data["external_transaction_id"] = external_transaction_id

            # Get the token using PeoplesPayService
            token = PeoplesPayService.get_token()
            print("Retrieved token:", token)  # Debug token retrieval

            if token is None:
                return Response(
                    {"message": "Failed to retrieve token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Prepare the payload
            card_payload = {
                "account_name": validated_data["account_name"],
                "amount": validated_data["amount"],
                "card": validated_data["card"],
                "description": validated_data["description"],
                "callbackUrl": validated_data["callbackUrl"],
                "clientRedirectUrl": validated_data["clientRedirectUrl"],
            }
            print("Payload prepared for PeoplesPay:", card_payload)  # Debug payload

            collection_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token['data']}",
            }
            print(
                "Headers for PeoplesPay request:", collection_headers
            )  # Debug headers

            try:
                card_response = requests.post(
                    f"{PeoplesPayService.BASE_URL}/collectmoney/card",
                    json=card_payload,
                    headers=collection_headers,
                )
                print(
                    "Response from PeoplesPay:", card_response.text
                )  # Debug raw response

                card_data = card_response.json()
                print(
                    "Parsed response data from PeoplesPay:", card_data
                )  # Debug parsed JSON

                card_transaction_id = card_data.get("transactionId")
                print(
                    "Extracted card_transaction_id:", card_transaction_id
                )  # Debug transaction ID

                if (
                    card_response.status_code == 200
                    and card_data["success"]
                    and card_transaction_id
                ):
                    print(
                        "Transaction successful. Saving record..."
                    )  # Debug success case

                    # Save validated data
                    card_serializer.save(
                        external_transaction_id=external_transaction_id,
                        card_transaction_id=card_transaction_id,
                    )
                    print("Record saved in database.")  # Debug successful save

                    return Response(
                        {
                            "message": "Collection processed successfully",
                            "external_transaction_id": str(external_transaction_id),
                            "card_transaction_id": card_transaction_id,
                            "collection_status": card_data["success"],
                            "redirect_url": card_data["redirectUrl"],
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    print(
                        "Transaction failed. PeoplesPay response:",
                        card_data.get("message", "Unknown error"),
                    )  # Debug failure case
                    return Response(
                        {"message": card_data.get("message", "Transaction failed")},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            except requests.exceptions.RequestException as e:
                print("Error during PeoplesPay request:", str(e))  # Debug request error
                return Response(
                    {"message": f"Error processing collection: {str(e)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            print(
                "Serializer is invalid. Errors:", card_serializer.errors
            )  # Debug serializer errors
            return Response(card_serializer.errors, status=status.HTTP_400_BAD_REQUEST)