from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAuthenticatedUser(BasePermission):
    """
    Пользователь должен быть аутентифицирован.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class IsAuthorOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or obj.author == request.user
