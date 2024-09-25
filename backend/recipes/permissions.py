from rest_framework.permissions import BasePermission, SAFE_METHODS

class IsAuthenticatedUser(BasePermission):
    """
    Пользователь должен быть аутентифицирован.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        # Разрешить чтение (GET, HEAD, OPTIONS) для всех пользователей
        if request.method in SAFE_METHODS:
            return True

        # Разрешить обновление только автору объекта
        return obj.author == request.user