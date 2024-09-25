from rest_framework.permissions import (
    IsAuthenticated,
    BasePermission,
    SAFE_METHODS
)


class IsOwnerOrReadOnly(IsAuthenticated):
    """
    Пользователь может изменять только свои данные.
    """
    def has_object_permission(self, request, view, obj):
        return obj == request.user


class IsAuthenticatedUser(BasePermission):
    def has_permission(self, request, view):
        return (request.method in SAFE_METHODS
                or request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return obj == request.user
