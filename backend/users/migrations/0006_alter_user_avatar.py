# Generated by Django 4.2.14 on 2024-07-21 10:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0005_alter_user_avatar"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="avatar",
            field=models.ImageField(
                blank=True,
                default="avatars/default_avatar.png",
                null=True,
                upload_to="avatars/",
            ),
        ),
    ]
