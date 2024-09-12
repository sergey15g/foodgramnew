# Generated by Django 4.2.14 on 2024-07-21 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_alter_user_avatar"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="avatar",
            field=models.ImageField(
                blank=True,
                default="avatars/default_avatar.png",
                null=True,
                upload_to="users/avatars/",
            ),
        ),
    ]
