# Generated by Django 4.2.15 on 2024-10-17 19:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worker_voucher', '0013_alter_groupofworker_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupofworker',
            name='name',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='historicalgroupofworker',
            name='name',
            field=models.CharField(max_length=50),
        ),
    ]
