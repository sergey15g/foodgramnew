# Generated by Django 4.2.14 on 2024-09-24 22:02

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("recipes", "0015_shortlink_alter_subscription_author"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Subscription",
        ),
    ]