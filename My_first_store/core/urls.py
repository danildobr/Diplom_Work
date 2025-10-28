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
    path('api/auth/register/', views.register_view, name='register'),
    path('api/auth/login/', views.login_view, name='login'),
    # path('api/auth/logout/', views.logout_view, name='logout'),
    path('api/auth/profile/', views.profile_view, name='profile'),
    path('api/', include(router.urls)),
]