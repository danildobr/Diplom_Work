# myapp/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import (
    Supplier, Category, Product, Parameter, ProductParameter,
    DeliveryAddress, Order, OrderItem
)

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
    '''Сериализует адрес доставки.'''
    class Meta:
        model = DeliveryAddress
        fields = '__all__'

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