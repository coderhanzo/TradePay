import os
import stat
from rest_framework.response import Response
import requests
from django.conf import settings
from rest_framework import status


class PeoplesPayService:
    BASE_URL = "https://peoplespay.com.gh/peoplepay/hub"

    @staticmethod
    def get_token(operation="DEBIT"):
        merchantId = os.getenv("PEOPLES_PAY_MERCHANT_ID")
        apikey = os.getenv("PEOPLES_PAY_API_KEY")

        if not merchantId or not apikey:
            raise ValueError("Merchant ID or API key not set in environment variables.")

        url = f"{PeoplesPayService.BASE_URL}/token/get"
        payload = {
            "merchantId": merchantId,
            "apikey": apikey,
            "operation": operation.upper(),
        }
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response_data = response.json()

            if response.status_code == 200 and "data" in response_data:
                return response_data
            else:
                return status.HTTP_400_BAD_REQUEST
        except requests.exceptions.RequestException as e:
            print(f"Error retrieving token: {e}")
            return Response(
                {"message": "Failed to retrieve token"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @staticmethod
    def disburse_money(
        token,
        amount,
        account_name,
        account_number,
        account_issuer,
        external_transaction_id,
        description,
    ):
        URL = f"{PeoplesPayService.BASE_URL}/disburse"
        payload = {
            "amount": str(amount),
            "account_number": account_number,
            "account_name": account_name,
            "account_issuer": account_issuer,
            "external_transaction_id": external_transaction_id,
            "description": description,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        reponse = requests.post(URL, json=payload, headers=headers)
        return reponse.json()

    @staticmethod
    def process_collection(
        token,
        amount,
        account_name,
        account_number,
        account_issuer,
        callbackUrl,
    ):
        URL = f"{PeoplesPayService.BASE_URL}/collectmoney"
        payload = {
            "amount": str(amount),
            "account_number": account_number,
            "account_name": account_name,
            "account_issuer": account_issuer,
            "callbackUrl": callbackUrl,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        reponse = requests.post(URL, json=payload, headers=headers)
        return reponse.json()
