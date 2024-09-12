from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True, verbose_name="Мыло")
    first_name = models.CharField(max_length=150, verbose_name="Имя")
    last_name = models.CharField(max_length=150, verbose_name="Фамилия")
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
        related_name="subscribed_to",
        on_delete=models.CASCADE,
        verbose_name="Юзверь",
    )
    subscribed_to = models.ForeignKey(
        User,
        related_name="subscribers",
        on_delete=models.CASCADE,
        verbose_name="Подписан на",
    )

    class Meta:
        unique_together = ("user", "subscribed_to")
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
