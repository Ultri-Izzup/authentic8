# Generated by Django 4.1.5 on 2023-01-10 19:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("authentik_blueprints", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="blueprintinstance",
            name="content",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="blueprintinstance",
            name="path",
            field=models.TextField(blank=True, default=""),
        ),
    ]
