from .models import User
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import (
    Supplier,
    Category,
    Product,
    Parameter,
    ProductParameter,
    DeliveryAddress,
    Order,
    OrderItem,
)
from .models import ORDER_STATUS_CHOICES
from .serializers import (
    SupplierSerializer,
    CategorySerializer,
    ProductSerializer,
    ParameterSerializer,
    ProductParameterSerializer,
    DeliveryAddressSerializer,
    OrderSerializer,
    OrderItemSerializer,
    UserSerializer,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status


class UserViewSet(viewsets.ModelViewSet):
    """API эндпоинт для управления пользователями."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Показываем только профиль текущего пользователя
        return User.objects.filter(id=self.request.user.id)


class SupplierViewSet(viewsets.ModelViewSet):
    """API эндпоинт для просмотра поставщиков."""
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [AllowAny]


class OrderViewSet(viewsets.ModelViewSet):
    """API эндпоинт для управления заказами."""
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Показываем только заказы текущего пользователя
        return Order.objects.filter(user=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    """API эндпоинт для просмотра категорий."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    """API эндпоинт для просмотра товаров."""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]


class ParameterViewSet(viewsets.ModelViewSet):
    """API эндпоинт для просмотра параметров."""
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer


class ProductParameterViewSet(viewsets.ModelViewSet):
    """API эндпоинт для просмотра параметров товаров."""
    queryset = ProductParameter.objects.all()
    serializer_class = ProductParameterSerializer


class DeliveryAddressViewSet(viewsets.ModelViewSet):
    """API эндпоинт для управления адресами доставки."""
    queryset = DeliveryAddress.objects.all()
    serializer_class = DeliveryAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DeliveryAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Привязываем адрес к текущему пользователю
        serializer.save(user=self.request.user)


class OrderItemViewSet(viewsets.ModelViewSet):
    """API эндпоинт для просмотра товаров в заказе."""
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]


### === Изменеие статуса заказа только Админы могут
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_order_status_view(request, order_id):
    """Обновляет статус заказа (только для администраторов)."""
    # Проверяем, является ли пользователь администратором
    if not (request.user.is_staff or request.user.is_superuser):
        return Response(
            {"error": "Недостаточно прав для изменения статуса заказа"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Получаем новый статус из тела запроса
    new_status = request.data.get("status")

    if new_status is None:
        return Response(
            {"error": "Не указан новый статус"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Проверим, что новый статус входит в допустимые
    valid_statuses = [choice[0] for choice in ORDER_STATUS_CHOICES]
    if new_status not in valid_statuses:
        return Response(
            {"error": f"Недопустимый статус. Допустимые: {valid_statuses}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({"error": "Заказ не найден"}, status=status.HTTP_404_NOT_FOUND)

    # Изменяем статус
    order.status = new_status
    order.save()

    # Сериализуем и возвращаем обновлённый заказ
    serializer = OrderSerializer(order)
    return Response(serializer.data, status=status.HTTP_200_OK)
