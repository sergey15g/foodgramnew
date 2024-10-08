from django.contrib.auth.models import AbstractUser
from django.db import models

from .constants import MAX_LENGHT_FIRST, MAX_LENGHT_NAME


class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name="Мыло")
    first_name = models.CharField(
        max_length=MAX_LENGHT_NAME,
        verbose_name="Имя",
    )
    last_name = models.CharField(
        max_length=MAX_LENGHT_FIRST,
        verbose_name="Фамилия",
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        default="avatars/default_avatar.png",
        null=True,
        blank=True,
        verbose_name="Аватар",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]


class Subscription(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="users_subscriptions",
        verbose_name="Юзверь",
    )
    subscribed_to = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="users_subscribers",
        verbose_name="Автор",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "subscribed_to"],
                name="unique_subscription_users",
            )
        ]
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"

    def __str__(self):
        return (f"{self.user.username} "
                f"подписан на {self.subscribed_to.username}")
