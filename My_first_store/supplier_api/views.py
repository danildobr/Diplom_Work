from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from core.models import Supplier, Category, Product, Parameter, ProductParameter, Order, OrderItem
from core.serializers import OrderSerializer, SupplierSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import viewsets



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
