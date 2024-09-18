from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Subscription, User


@admin.register(User)
class UserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (
            'Personal info',
            {'fields': ('first_name', 'last_name', 'email', 'avatar')},
        ),
        (
            'Permissions',
            {
                'fields': (
                    'is_active',
                    'is_staff',
                    'is_superuser',
                    'groups',
                    'user_permissions',
                )
            },
        ),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': (
                    'username',
                    'email',
                    'password1',
                    'password2',
                    'first_name',
                    'last_name',
                    'avatar',
                ),
            },
        ),
    )
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'avatar',
    )
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('id',)
    actions = ['delete_selected']


@admin.register(Subscription)
class SubscribeAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'subscribed_to',
    )
