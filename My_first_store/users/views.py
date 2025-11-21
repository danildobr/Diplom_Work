from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from core.models import User
from core.serializers import UserSerializer


# Регистрация
@api_view(["POST"])
@permission_classes([AllowAny])
def register_view(request):
    """Создаёт нового пользователя."""
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {"user": UserSerializer(user).data, "token": token.key},
            status=status.HTTP_201_CREATED,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Логин
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    """Аутентифицирует пользователя и возвращает токен."""
    username = request.data.get("username")
    password = request.data.get("password")

    user = authenticate(username=username, password=password)
    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {"user": UserSerializer(user).data, "token": token.key},
            status=status.HTTP_200_OK,
        )
    else:
        return Response(
            {"error": "Неверные учетные данные"}, status=status.HTTP_400_BAD_REQUEST
        )


# Профиль (требует аутентификации)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """Возвращает профиль аутентифицированного пользователя."""
    return Response(UserSerializer(request.user).data)
