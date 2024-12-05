from django.urls import path
from . import views


urlpatterns = [
    path("payments/", views.PaymentsView.as_view()),
    path("collections/", views.CollectionsView.as_view()),
    path(
        "payment-callback/",
        views.PaymentCallbackAPIView.as_view(),
        name="payment-callback",
    ),
    path("token/", views.TokenView.as_view()),
]
