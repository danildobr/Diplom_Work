from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views  

router = DefaultRouter()
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'categories', views.CategoryViewSet)
router.register(r'products', views.ProductViewSet)
router.register(r'parameters', views.ParameterViewSet)
router.register(r'product-parameters', views.ProductParameterViewSet)
router.register(r'delivery-addresses', views.DeliveryAddressViewSet)
router.register(r'order-items', views.OrderItemViewSet)
router.register(r'orders', views.OrderViewSet)
router.register(r'users', views.UserViewSet)

urlpatterns = [
    path('api/orders/<int:order_id>/status/', views.update_order_status_view, name='update-order-status'),
    path('api/', include(router.urls)),
]
