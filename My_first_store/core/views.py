from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from . models import Basket, BasketItem
from django.utils import timezone
from datetime import timedelta
from . serializers import BasketSerializer, BasketItemSerializer
from django.shortcuts import render
from . models import User
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from . models import (
    Supplier, OrderConfirmationCode, Category, Product, Parameter, ProductParameter,
    DeliveryAddress, Order, OrderItem
)
from django.utils.html import strip_tags
import random
import string
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.models import Group 
from .models import ORDER_STATUS_CHOICES
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
from django.db import transaction 



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

    basket_items = basket.items.all()
    if not basket_items.exists():
        return Response({'error': 'Корзина пуста'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем, есть ли товары в корзине
    # Проверяем, принимает ли поставщик заказы
    for item in basket_items:
        if not item.product.supplier.accepts_orders:
            return Response({
                'error': f'Поставщик "{item.product.supplier.name}" не принимает заказы. Невозможно оформить заказ с товаром "{item.product.name}".'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем количество товара на складе
        if item.product.quantity < item.quantity:
            return Response({
                'error': f'Недостаточно товара "{item.product.name}" на складе. Запрошено: {item.quantity}, доступно: {item.product.quantity}'
            }, status=status.HTTP_400_BAD_REQUEST)

    # Получаем адрес доставки из тела запроса
    address_id = request.data.get('delivery_address_id')
    if not address_id:
        return Response({'error': 'Не указан адрес доставки'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем, что адрес принадлежит пользователю
    try:
        address = DeliveryAddress.objects.get(id=address_id, user=request.user)
    except DeliveryAddress.DoesNotExist:
        return Response({'error': 'Адрес доставки не найден или не принадлежит пользователю'}, status=status.HTTP_400_BAD_REQUEST)

    # Если всё ок, создаём заказ
    order = Order.objects.create(user=request.user, address=address, status='new') # <-- Статус 'new'

    # Создаём OrderItem для каждого товара в корзине
    # НЕ УМЕНЬШАЕМ количество на складе пока
    for item in basket_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity
        )

    # Генерируем код подтверждения
    confirmation_code = ''.join(random.choices(string.digits, k=6))
    expires_at = timezone.now() + timedelta(minutes=15) # Код действует 15 минут

    OrderConfirmationCode.objects.create(
        order=order,
        code=confirmation_code,
        expires_at=expires_at
    )

    # --- Отправка email с кодом подтверждения ---

    subject_client = f'Подтверждение заказа #{order.id}'
    html_message_client = render_to_string('email/order_confirmation_request.html', {
        'order': order,
        'confirmation_code': confirmation_code
    })
    plain_message_client = strip_tags(html_message_client)
    send_mail(
        subject_client,
        plain_message_client,
        None,  # Используем DEFAULT_FROM_EMAIL
        [request.user.email],  # Email клиента
        html_message=html_message_client,
    )

    # Возвращаем информацию о созданном заказе (пока не подтверждён)
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
                return Response({'message': 'Товар удалён из корзины'}, status=status.HTTP_200_OK)
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


# API-эндпоинт, чтобы поставщик мог изменить это поле через API.

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def toggle_supplier_accepts_orders(request):
    try:
        supplier = request.user.supplier_profile
    except Supplier.DoesNotExist:
        return Response({'error': 'Пользователь не является поставщиком'}, status=status.HTTP_403_FORBIDDEN)

    new_status = request.data.get('accepts_orders')
    if new_status is None:
        return Response({'error': 'Не указано новое состояние'}, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(new_status, bool):
        return Response({'error': 'Значение должно быть true или false'}, status=status.HTTP_400_BAD_REQUEST)

    supplier.accepts_orders = new_status
    supplier.save()

    return Response({'accepts_orders': supplier.accepts_orders}, status=status.HTTP_200_OK)


# Получать список оформленных заказов 
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def supplier_orders_view(request):
    # Проверяем, является ли пользователь поставщиком
    try:
        supplier = request.user.supplier_profile
    except Supplier.DoesNotExist:
        return Response({'error': 'Пользователь не является поставщиком'}, status=status.HTTP_403_FORBIDDEN)

    # Находим заказы, в которых есть товары от этого поставщика
    orders = Order.objects.filter(items__product__supplier=supplier).distinct()

    # Сериализуем заказы
    serializer = OrderSerializer(orders, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)



# API-эндпоинт, через который поставщик сможет загружать/обновлять свои товары в базу данных через API,
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def supplier_upload_price_view(request):
    # Проверяем, является ли пользователь поставщиком
    try:
        supplier = request.user.supplier_profile
    except Supplier.DoesNotExist:
        return Response({'error': 'Пользователь не является поставщиком'}, status=status.HTTP_403_FORBIDDEN)

    # Получаем данные из тела запроса
    data = request.data

    # Проверяем структуру данных
    if not isinstance(data, dict) or 'goods' not in data:
        return Response({'error': 'Неверный формат данных. Ожидается объект с полем "goods".'}, status=status.HTTP_400_BAD_REQUEST)

    # Начинаем транзакцию для атомарности операций
    with transaction.atomic():
        # Создаём/обновим категории
        category_map = {}
        for cat_data in data.get('categories', []):
            cat, _ = Category.objects.get_or_create(
                id=cat_data['id'],
                defaults={'name': cat_data['name']}
            )
            category_map[cat_data['id']] = cat

        # Создаём/обновим параметры
        parameter_map = {}
        for good in data['goods']:
            for param_name in good['parameters']:
                param, _ = Parameter.objects.get_or_create(name=param_name)
                parameter_map[param_name] = param

        # Обрабатываем товары
        created_count = 0
        updated_count = 0
        for good in data['goods']:
            category = category_map.get(good['category'])
            if not category:
                return Response({'error': f'Категория с ID {good["category"]} не найдена.'}, status=status.HTTP_400_BAD_REQUEST)

            # Используем external_id и supplier для уникальности
            product, created = Product.objects.get_or_create(
                external_id=good['id'],
                supplier=supplier,
                defaults={
                    'name': good['name'],
                    'category': category,
                    'price': good['price'],
                    'quantity': good['quantity']
                }
            )

            if not created:
                # Если товар уже был, обновим поля
                product.name = good['name']
                product.category = category
                product.price = good['price']
                product.quantity = good['quantity']
                product.save()
                updated_count += 1
            else:
                created_count += 1

            for param_name, param_value in good['parameters'].items():
                param = parameter_map[param_name]
                ProductParameter.objects.update_or_create(
                    product=product,
                    parameter=param,
                    defaults={'value': str(param_value)}
                )
    
    return Response({
            'message': 'Прайс-лист успешно загружен',
            'created': created_count,
            'updated': updated_count
        }, status=status.HTTP_201_CREATED)
    
    
### === Изменеие статуса заказа только Админы могут
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_order_status_view(request, order_id):
    # Проверяем, является ли пользователь администратором
    # (Можно проверить по группе или по is_staff)
    if not (request.user.is_staff or request.user.is_superuser):
        # Или проверить по группе:
        # if not request.user.groups.filter(name='Администраторы').exists():
        return Response({'error': 'Недостаточно прав для изменения статуса заказа'}, status=status.HTTP_403_FORBIDDEN)

    # Получаем новый статус из тела запроса
    new_status = request.data.get('status')

    if new_status is None:
        return Response({'error': 'Не указан новый статус'}, status=status.HTTP_400_BAD_REQUEST)

    # Проверим, что новый статус входит в допустимые
    valid_statuses = [choice[0] for choice in ORDER_STATUS_CHOICES]
    if new_status not in valid_statuses:
        return Response({'error': f'Недопустимый статус. Допустимые: {valid_statuses}'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({'error': 'Заказ не найден'}, status=status.HTTP_404_NOT_FOUND)

    # Изменяем статус
    order.status = new_status
    order.save()

    # Сериализуем и возвращаем обновлённый заказ
    serializer = OrderSerializer(order)
    return Response(serializer.data, status=status.HTTP_200_OK)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def confirm_order_view(request):
    order_id = request.data.get('order_id')
    code = request.data.get('confirmation_code')

    if not order_id or not code:
        return Response({'error': 'Не указан ID заказа или код подтверждения'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response({'error': 'Заказ не найден или не принадлежит пользователю'}, status=status.HTTP_404_NOT_FOUND)

    try:
        confirmation_code_obj = OrderConfirmationCode.objects.get(order=order)
    except OrderConfirmationCode.DoesNotExist:
        return Response({'error': 'Код подтверждения не найден для этого заказа'}, status=status.HTTP_400_BAD_REQUEST)

    if confirmation_code_obj.is_expired():
        confirmation_code_obj.delete() # Удаляем истёкший код
        return Response({'error': 'Код подтверждения истёк'}, status=status.HTTP_400_BAD_REQUEST)

    if confirmation_code_obj.code != code:
        return Response({'error': 'Неверный код подтверждения'}, status=status.HTTP_400_BAD_REQUEST)

    # --- Код верен и не истёк ---
    # Уменьшаем количество на складе
    for item in order.items.all():
        item.product.quantity -= item.quantity
        item.product.save()

    # Меняем статус заказа
    order.status = 'confirmed'
    order.save()

    # Удаляем код подтверждения
    confirmation_code_obj.delete()

    # Очищаем корзину (если нужно, хотя она уже была "перенесена" в заказ)
    basket = Basket.objects.get(user=request.user)
    basket.items.all().delete()

    # Возвращаем информацию о подтверждённом заказе
    serializer = OrderSerializer(order)
    return Response(serializer.data, status=status.HTTP_200_OK)


#востановление пароля
# --- 1. Запрос на восстановление пароля (отправка письма) ---

class PasswordResetRequestView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        email = data.get('email')

        if not email:
            return JsonResponse({'error': 'Email обязателен'}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Не сообщаем, существует ли пользователь, для безопасности
            return JsonResponse({'message': 'Если email существует, письмо с инструкциями отправлено.'}, status=200)

        # Генерируем токен и UID
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Формируем ссылку (например, для фронтенда)
        # В реальном приложении это будет URL вашего фронтенда
        reset_url = f"http://your-frontend.com/reset-password/{uid}/{token}/"

        # Отправляем письмо
        subject = 'Сброс пароля'
        html_message = render_to_string('email/password_reset_email.html', {
            'user': user,
            'reset_url': reset_url,
        })
        plain_message = strip_tags(html_message)
        from_email = None  # Используем DEFAULT_FROM_EMAIL

        send_mail(
            subject,
            plain_message,
            from_email,
            [user.email],
            html_message=html_message,
        )

        return JsonResponse({'message': 'Если email существует, письмо с инструкциями отправлено.'}, status=200)

# --- 2. Подтверждение сброса пароля (установка нового пароля) ---

class PasswordResetConfirmView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        uidb64 = data.get('uid')
        token = data.get('token')
        new_password = data.get('new_password')

        if not uidb64 or not token or not new_password:
            return JsonResponse({'error': 'UID, token и новый пароль обязательны'}, status=400)

        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            # Устанавливаем новый пароль
            user.set_password(new_password)
            user.save()
            return JsonResponse({'message': 'Пароль успешно изменён'}, status=200)
        else:
            return JsonResponse({'error': 'Ссылка для сброса пароля недействительна'}, status=400)