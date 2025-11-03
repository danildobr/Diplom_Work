from django.shortcuts import render

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from core.models import Basket, BasketItem, Product  
from core.serializers import BasketSerializer, BasketItemSerializer  


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

