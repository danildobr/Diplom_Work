from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # Подключаем маршруты из новых приложений
    path("", include("users.urls")),
    path("", include("basket.urls")),
    path("", include("orders.urls")),
    path("", include("supplier_api.urls")),
    path("", include("core.urls")),
]
