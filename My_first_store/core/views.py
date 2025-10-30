from . models import Basket, BasketItem
from . serializers import BasketSerializer, BasketItemSerializer
from django.shortcuts import render
from . models import User
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from . models import (
    Supplier, Category, Product, Parameter, ProductParameter,
    DeliveryAddress, Order, OrderItem
)
from . serializers import (
    SupplierSerializer, CategorySerializer, ProductSerializer,
    ParameterSerializer, ProductParameterSerializer,
    DeliveryAddressSerializer, OrderSerializer, OrderItemSerializer,
    UserSerializer
)
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate, login, logout




class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [AllowAny]


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]


class ParameterViewSet(viewsets.ModelViewSet):
    queryset = Parameter.objects.all()
    serializer_class = ParameterSerializer


class ProductParameterViewSet(viewsets.ModelViewSet):
    queryset = ProductParameter.objects.all()
    serializer_class = ProductParameterSerializer

class DeliveryAddressViewSet(viewsets.ModelViewSet):
    queryset = DeliveryAddress.objects.all()
    serializer_class = DeliveryAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DeliveryAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Привязываем адрес к текущему пользователю
        serializer.save(user=self.request.user)

class OrderItemViewSet(viewsets.ModelViewSet):
    queryset = OrderItem.objects.all()
    serializer_class = OrderItemSerializer
    permission_classes = [IsAuthenticated]
    

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Показываем только заказы текущего пользователя
        return Order.objects.filter(user=self.request.user)
    

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Показываем только профиль текущего пользователя
        return User.objects.filter(id=self.request.user.id) 
    
    
# Регистрация
@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# Логин
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)
    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Неверные учетные данные'}, status=status.HTTP_400_BAD_REQUEST)

# Логаут (только если используем SessionAuthentication)
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def logout_view(request):
#     logout(request)
#     return Response({'message': 'Успешный выход'}, status=status.HTTP_200_OK)

# Профиль (требует аутентификации)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    return Response(UserSerializer(request.user).data)


#логика работы с корзиной
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def basket_view(request):
    basket, created = Basket.objects.get_or_create(user=request.user)
    serializer = BasketSerializer(basket)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def basket_add_view(request):
    product_id = request.data.get('product_id')
    quantity = request.data.get('quantity', 1)

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        return Response({'error': 'Товар не найден'}, status=status.HTTP_404_NOT_FOUND)

    basket, created = Basket.objects.get_or_create(user=request.user)
    basket_item, created = BasketItem.objects.get_or_create(
        basket=basket,
        product=product,
        defaults={'quantity': quantity}
    )

    if not created:
        basket_item.quantity += int(quantity)
        basket_item.save()

    serializer = BasketItemSerializer(basket_item)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def basket_remove_view(request, item_id):
    try:
        basket_item = BasketItem.objects.get(id=item_id, basket__user=request.user)
    except BasketItem.DoesNotExist:
        return Response({'error': 'Товар не найден в корзине'}, status=status.HTTP_404_NOT_FOUND)

    basket_item.delete()
    return Response({'message': 'Товар удалён из корзины'}, status=status.HTTP_204_NO_CONTENT)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def order_create_view(request):
    # Получаем корзину пользователя
    try:
        basket = Basket.objects.get(user=request.user)
    except Basket.DoesNotExist:
        return Response({'error': 'Корзина пуста'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем, есть ли товары в корзине
    basket_items = basket.items.all()
    if not basket_items.exists():
        return Response({'error': 'Корзина пуста'}, status=status.HTTP_400_BAD_REQUEST)

    # Получаем адрес доставки из тела запроса
    address_id = request.data.get('delivery_address_id')
    if not address_id:
        return Response({'error': 'Не указан адрес доставки'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем, что адрес принадлежит пользователю
    try:
        address = DeliveryAddress.objects.get(id=address_id, user=request.user)
    except DeliveryAddress.DoesNotExist:
        return Response({'error': 'Адрес доставки не найден или не принадлежит пользователю'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем количество товаров в корзине
    for item in basket_items:
        if item.product.quantity < item.quantity:
            return Response({
                'error': f'Недостаточно товара "{item.product.name}" на складе. Запрошено: {item.quantity}, доступно: {item.product.quantity}'
            }, status=status.HTTP_400_BAD_REQUEST)

    # Если всё ок, создаём заказ
    order = Order.objects.create(user=request.user, address=address, status='new')

    # Создаём OrderItem для каждого товара в корзине
    # И уменьшаем количество на складе
    for item in basket_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity
        )
        # Уменьшаем количество товара на складе
        item.product.quantity -= item.quantity
        item.product.save()

    # Очищаем корзину
    basket.items.all().delete()

    # Возвращаем информацию о созданном заказе
    serializer = OrderSerializer(order)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def basket_update_quantity_view(request, item_id):
    try:
        basket_item = BasketItem.objects.get(id=item_id, basket__user=request.user)
    except BasketItem.DoesNotExist:
        return Response({'error': 'Товар не найден в корзине'}, status=status.HTTP_404_NOT_FOUND)

    new_quantity = request.data.get('quantity')

    if new_quantity is None:
        return Response({'error': 'Не указано новое количество'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        new_quantity = int(new_quantity)
        if new_quantity <= 0:
            # Если количество <= 0, можно автоматически удалить
            basket_item.delete()
            return Response({'message': 'Товар удалён из корзины (количество <= 0)'}, status=status.HTTP_204_NO_CONTENT)
    except ValueError:
        return Response({'error': 'Количество должно быть числом'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверим, достаточно ли товара на складе
    if basket_item.product.quantity < new_quantity:
        return Response({
            'error': f'Недостаточно товара "{basket_item.product.name}" на складе. Запрошено: {new_quantity}, доступно: {basket_item.product.quantity}'
        }, status=status.HTTP_400_BAD_REQUEST)

    basket_item.quantity = new_quantity
    basket_item.save()

    serializer = BasketItemSerializer(basket_item)
    return Response(serializer.data, status=status.HTTP_200_OK)