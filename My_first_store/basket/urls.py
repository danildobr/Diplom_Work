
from django.urls import path
from . import views  

urlpatterns = [
    path('api/basket/', views.basket_view, name='basket'),
    path('api/basket/add/', views.basket_add_view, name='basket-add'),
    path('api/basket/remove/<int:item_id>/', views.basket_remove_view, name='basket-remove'),
    path('api/basket/update/<int:item_id>/', views.basket_update_quantity_view, name='basket-update-quantity'),
]