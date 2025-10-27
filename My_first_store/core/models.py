from django.db import models

# Create your models here.
# models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator

# Типы пользователей
USER_TYPE_CHOICES = (
    ('client', 'Клиент'),
    ('supplier', 'Поставщик'),
)

ORDER_STATUS_CHOICES = (
    ('new', 'Новый'),
    ('confirmed', 'Подтверждён'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменён'),
)


class User(AbstractUser):
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='client')
    email = models.EmailField(unique=True)

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"


class Supplier(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='supplier_profile')
    name = models.CharField(max_length=255, verbose_name="Название компании")
    accepts_orders = models.BooleanField(default=True, verbose_name="Принимает заказы")

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantity = models.PositiveIntegerField(default=0)
    external_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID из прайса поставщика")

    class Meta:
        unique_together = ('supplier', 'external_id')  # чтобы не дублировать импорт

    def __str__(self):
        return f"{self.name} ({self.supplier.name})"


class Parameter(models.Model):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class ProductParameter(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='parameters')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    value = models.TextField()

    class Meta:
        unique_together = ('product', 'parameter')

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"


class DeliveryAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='addresses')
    city = models.CharField(max_length=100)
    street = models.CharField(max_length=255)
    house = models.CharField(max_length=20)
    apartment = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.city}, {self.street}, д.{self.house}"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    address = models.ForeignKey(DeliveryAddress, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='new')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Заказ #{self.id} от {self.user.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        unique_together = ('order', 'product')

    def __str__(self):
        return f"{self.product.name} x{self.quantity}"