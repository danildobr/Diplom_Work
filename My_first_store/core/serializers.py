# myapp/serializers.py
from rest_framework import serializers
from django.core.exceptions import ValidationError
from .models import User  
from . models import (
    Supplier, Category, Product, Parameter, ProductParameter,
    DeliveryAddress, Order, OrderItem
)
from . models import Basket, BasketItem

# Сериализаторы для вспомогательных моделей

class ParameterSerializer(serializers.ModelSerializer):
    '''Просто конвертирует модель Parameter (например, "Цвет", "Диагональ")'''
    class Meta:
        model = Parameter
        fields = '__all__'

class ProductParameterSerializer(serializers.ModelSerializer):
    '''Конвертирует ProductParameter (например, "Цвет: черный").'''
    parameter = ParameterSerializer(read_only=True)
    class Meta:
        model = ProductParameter
        fields = ['parameter', 'value']

class CategorySerializer(serializers.ModelSerializer):
    '''Просто сериализуют Category'''
    class Meta:
        model = Category
        fields = '__all__'

class SupplierSerializer(serializers.ModelSerializer):
    '''Просто сериализуют Category и Supplier'''
    class Meta:
        model = Supplier
        fields = '__all__'

# Основные сериализаторы

class ProductSerializer(serializers.ModelSerializer):
    parameters = ProductParameterSerializer(source='productparameter_set', many=True, read_only=True)
    category = CategorySerializer(read_only=True)
    supplier = SupplierSerializer(read_only=True)

    class Meta:
        model = Product
        fields = '__all__'

class DeliveryAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryAddress
        fields = '__all__'

    def validate(self, attrs):
        # Получаем пользователя из контекста (передаётся из ViewSet)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user = request.user
        else:
            # Если контекста нет, значит, это не через API вызывается — можно пропустить
            # или вызвать ValidationError
            raise ValidationError("Контекст запроса с пользователем обязателен.")

        # Проверяем, существует ли уже такой адрес у пользователя
        city = attrs.get('city')
        street = attrs.get('street')
        house = attrs.get('house')
        apartment = attrs.get('apartment')

        if DeliveryAddress.objects.filter(
            user=user,
            city=city,
            street=street,
            house=house,
            apartment=apartment
        ).exists():
            raise ValidationError('Адрес доставки с такими параметрами уже существует для этого пользователя.')
        return attrs


class OrderItemSerializer(serializers.ModelSerializer):
    '''Сериализует один товар в заказе.'''
    product = ProductSerializer(read_only=True)
    class Meta:
        model = OrderItem
        fields = ['product', 'quantity']

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(source='orderitem_set', many=True, read_only=True)
#   список товаров в заказе
    address = DeliveryAddressSerializer(read_only=True)
#   информация о адресе доставки.
    class Meta:
        model = Order
        fields = '__all__'

        
class UserSerializer(serializers.ModelSerializer):
    '''Cериализатор для регистрации'''
    password = serializers.CharField(write_only=True)  # Пароль не будет возвращаться в JSON

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'user_type']

    def create(self, validated_data):
        # Хешируем пароль при создании пользователя
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    
# модкль корзины 
class BasketItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)  # Выводим полную информацию о товаре

    class Meta:
        model = BasketItem
        fields = ['id', 'product', 'quantity']

class BasketSerializer(serializers.ModelSerializer):
    items = BasketItemSerializer(source='items.all', many=True, read_only=True)  # Все товары в корзине
    total_quantity = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Basket
        fields = ['id', 'items', 'total_quantity', 'total_price', 'created_at', 'updated_at']

    def get_total_quantity(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_total_price(self, obj):
        return sum(item.product.price * item.quantity for item in obj.items.all())