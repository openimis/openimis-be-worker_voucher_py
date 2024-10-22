# Generated by Django 4.2.15 on 2024-10-15 14:30

import core.fields
import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('worker_voucher', '0010_groupofworker_workergroup_historicalworkergroup_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalworkergroup',
            name='date_valid_from',
            field=core.fields.DateTimeField(db_column='DateValidFrom', default=datetime.datetime.now),
        ),
        migrations.AddField(
            model_name='historicalworkergroup',
            name='date_valid_to',
            field=core.fields.DateTimeField(blank=True, db_column='DateValidTo', null=True),
        ),
        migrations.AddField(
            model_name='historicalworkergroup',
            name='replacement_uuid',
            field=models.UUIDField(blank=True, db_column='ReplacementUUID', null=True),
        ),
        migrations.AddField(
            model_name='workergroup',
            name='date_valid_from',
            field=core.fields.DateTimeField(db_column='DateValidFrom', default=datetime.datetime.now),
        ),
        migrations.AddField(
            model_name='workergroup',
            name='date_valid_to',
            field=core.fields.DateTimeField(blank=True, db_column='DateValidTo', null=True),
        ),
        migrations.AddField(
            model_name='workergroup',
            name='replacement_uuid',
            field=models.UUIDField(blank=True, db_column='ReplacementUUID', null=True),
        ),
    ]
