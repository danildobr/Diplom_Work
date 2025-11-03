# supplier_api/urls.py

from django.urls import path
from . import views  # <-- Импортируем из supplier_api.views

urlpatterns = [
    path('api/supplier/upload-price/', views.supplier_upload_price_view, name='supplier-upload-price'),
    path('api/supplier/toggle-accepts-orders/', views.toggle_supplier_accepts_orders, name='toggle-supplier-accepts-orders'),
    path('api/supplier/orders/', views.supplier_orders_view, name='supplier-orders'),
]