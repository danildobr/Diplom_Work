from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
import random
import string
from core.models import (
    Order,
    OrderItem,
    DeliveryAddress,
    Basket,
    BasketItem,
    OrderConfirmationCode,
)
from core.serializers import OrderSerializer, OrderItemSerializer
from rest_framework import viewsets


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def order_create_view(request):
    """Создаёт новый заказ из корзины аутентифицированного пользователя."""
    # Получаем корзину пользователя
    try:
        basket = Basket.objects.get(user=request.user)
    except Basket.DoesNotExist:
        return Response({"error": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)

    basket_items = basket.items.all()
    if not basket_items.exists():
        return Response({"error": "Корзина пуста"}, status=status.HTTP_400_BAD_REQUEST)

    # Проверяем, есть ли товары в корзине
    # Проверяем, принимает ли поставщик заказы
    for item in basket_items:
        if not item.product.supplier.accepts_orders:
            return Response(
                {
                    "error": f'Поставщик "{item.product.supplier.name}" не принимает заказы. Невозможно оформить заказ с товаром "{item.product.name}".'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Проверяем количество товара на складе
        if item.product.quantity < item.quantity:
            return Response(
                {
                    "error": f'Недостаточно товара "{item.product.name}" на складе. Запрошено: {item.quantity}, доступно: {item.product.quantity}'
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

    # Получаем адрес доставки из тела запроса
    address_id = request.data.get("delivery_address_id")
    if not address_id:
        return Response(
            {"error": "Не указан адрес доставки"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        address_id = int(address_id)
        if address_id < 0:  # Проверяем, что число неотрицательное
            return Response(
                {"error": "ID адреса доставки не может быть отрицательным"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except (ValueError, TypeError):
        return Response(
            {"error": "ID адреса доставки должен быть целым числом"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Проверяем, что адрес принадлежит пользователю
    try:
        address = DeliveryAddress.objects.get(id=address_id, user=request.user)
    except DeliveryAddress.DoesNotExist:
        return Response(
            {"error": "Адрес доставки не найден или не принадлежит пользователю"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Если всё ок, создаём заказ
    order = Order.objects.create(
        user=request.user, address=address, status="new"
    )  # <-- Статус 'new'

    # Создаём OrderItem для каждого товара в корзине
    # НЕ УМЕНЬШАЕМ количество на складе пока
    for item in basket_items:
        OrderItem.objects.create(
            order=order, product=item.product, quantity=item.quantity
        )

    # Генерируем код подтверждения
    confirmation_code = "".join(random.choices(string.digits, k=6))
    expires_at = timezone.now() + timedelta(minutes=15)  # Код действует 15 минут

    OrderConfirmationCode.objects.create(
        order=order, code=confirmation_code, expires_at=expires_at
    )

    # --- Отправка email с кодом подтверждения ---

    subject_client = f"Подтверждение заказа #{order.id}"
    html_message_client = render_to_string(
        "email/order_confirmation_request.html",
        {"order": order, "confirmation_code": confirmation_code},
    )
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_order_view(request):
    """Подтверждает заказ с помощью кода подтверждения."""
    order_id = request.data.get("order_id")
    code = request.data.get("confirmation_code")

    if not order_id or not code:
        return Response(
            {"error": "Не указан ID заказа или код подтверждения"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        order_id = int(order_id)
        if order_id < 0:  # Проверка на неотрицательность
            return Response(
                {"error": "ID заказа не может быть отрицательным"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    except (ValueError, TypeError):
        return Response(
            {"error": "ID заказа должен быть целым числом"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        order = Order.objects.get(id=order_id, user=request.user)
    except Order.DoesNotExist:
        return Response(
            {"error": "Заказ не найден или не принадлежит пользователю"},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        confirmation_code_obj = OrderConfirmationCode.objects.get(order=order)
    except OrderConfirmationCode.DoesNotExist:
        return Response(
            {"error": "Код подтверждения не найден для этого заказа"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if confirmation_code_obj.is_expired():
        confirmation_code_obj.delete()  # Удаляем истёкший код
        return Response(
            {"error": "Код подтверждения истёк"}, status=status.HTTP_400_BAD_REQUEST
        )

    if confirmation_code_obj.code != code:
        return Response(
            {"error": "Неверный код подтверждения"}, status=status.HTTP_400_BAD_REQUEST
        )

    # --- Код верен и не истёк ---
    # Уменьшаем количество на складе
    for item in order.items.all():
        item.product.quantity -= item.quantity
        item.product.save()

    # Меняем статус заказа
    order.status = "confirmed"
    order.save()

    # Удаляем код подтверждения
    confirmation_code_obj.delete()

    # Очищаем корзину (если нужно, хотя она уже была "перенесена" в заказ)
    basket = Basket.objects.get(user=request.user)
    basket.items.all().delete()

    # Возвращаем информацию о подтверждённом заказе
    serializer = OrderSerializer(order)
    return Response(serializer.data, status=status.HTTP_200_OK)
