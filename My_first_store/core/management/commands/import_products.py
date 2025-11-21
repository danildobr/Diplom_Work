# myapp/management/commands/import_products.py

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Category, Supplier, Product, Parameter, ProductParameter

# from models import User
from django.contrib.auth import get_user_model

from data_json import data

User = get_user_model()


class Command(BaseCommand):
    help = "Импортирует товары из data_json.py в базу данных"

    def handle(self, *args, **options):
        shop_name = data["shop"]

        # Найдём или создадим **пользователя** с типом 'supplier'
        supplier_user, created = User.objects.get_or_create(
            username=shop_name,
            defaults={
                "email": f"{shop_name.lower()}@example.com",  # или другой email
                "user_type": "supplier",
                "is_active": True,
            },
        )
        if created:
            # Устанавливаем пароль по умолчанию или генерируем
            supplier_user.set_password(
                "default_password"
            )  # или используйте что-то более безопасное
            supplier_user.save()
            self.stdout.write(
                f"Создан пользователь поставщика: {supplier_user.username}"
            )

        # Найдём или создадим поставщика, привязанного к этому пользователю
        supplier, created = Supplier.objects.get_or_create(
            name=shop_name,
            defaults={
                "user": supplier_user,  # <-- ВАЖНО: передаём user
                "accepts_orders": True,
            },
        )
        if created:
            self.stdout.write(f"Создан поставщик: {supplier.name}")

        # Создаём категории
        category_map = {}
        for cat_data in data["categories"]:
            cat, _ = Category.objects.get_or_create(
                id=cat_data["id"], defaults={"name": cat_data["name"]}
            )
            category_map[cat_data["id"]] = cat

        # Создаём параметры
        parameter_map = {}
        for good in data["goods"]:
            for param_name in good["parameters"]:
                param, _ = Parameter.objects.get_or_create(name=param_name)
                parameter_map[param_name] = param

        # Создаём товары и их параметры
        for good in data["goods"]:
            category = category_map[good["category"]]

            product, created = Product.objects.get_or_create(
                external_id=good["id"],
                supplier=supplier,
                defaults={
                    "name": good["name"],
                    "category": category,
                    "price": good["price"],
                    "quantity": good["quantity"],
                },
            )

            if created:
                self.stdout.write(f"Создан товар: {product.name}")
            else:
                # Если товар уже был, можно обновить поля, например, цену и количество
                product.price = good["price"]
                product.quantity = good["quantity"]
                product.save()
                self.stdout.write(f"Обновлён товар: {product.name}")

            # Создаём ProductParameter
            for param_name, param_value in good["parameters"].items():
                param = parameter_map[param_name]
                ProductParameter.objects.get_or_create(
                    product=product,
                    parameter=param,
                    defaults={"value": str(param_value)},
                )

        self.stdout.write(self.style.SUCCESS("Импорт успешно завершён!"))
