from django.urls import path
from . import views

urlpatterns = [
    path("api/orders/create/", views.order_create_view, name="order-create"),
    path("api/orders/confirm/", views.confirm_order_view, name="order-confirm"),
]
