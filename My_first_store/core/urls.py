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
    path('api/auth/profile/', views.profile_view, name='profile'),
    path('api/basket/', views.basket_view, name='basket'),
    path('api/basket/add/', views.basket_add_view, name='basket-add'),
    path('api/basket/remove/<int:item_id>/', views.basket_remove_view, name='basket-remove'),
    path('api/orders/create/', views.order_create_view, name='order-create'),
    path('api/basket/update/<int:item_id>/', views.basket_update_quantity_view, name='basket-update-quantity'),
    path('api/supplier/toggle-accepts-orders/', views.toggle_supplier_accepts_orders, name='toggle-supplier-accepts-orders'),
    path('api/supplier/orders/', views.supplier_orders_view, name='supplier-orders'),
    path('api/supplier/upload-price/', views.supplier_upload_price_view, name='supplier-upload-price'),
    path('api/orders/<int:order_id>/status/', views.update_order_status_view, name='update-order-status'),
    path('api/orders/confirm/', views.confirm_order_view, name='order-confirm'), 
    path('api/auth/password-reset/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('api/auth/password-reset-confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    path('api/', include(router.urls)),
]