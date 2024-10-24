# Generated by Django 4.2.15 on 2024-10-10 11:14

import core.fields
import datetime
import dirtyfields.dirtyfields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('policyholder', '0018_alter_historicalpolicyholder_date_created_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('worker_voucher', '0007_alter_historicalworkervoucher_assigned_date_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkerUpload',
            fields=[
                ('id', models.UUIDField(db_column='UUID', default=None, editable=False, primary_key=True, serialize=False)),
                ('is_deleted', models.BooleanField(db_column='isDeleted', default=False)),
                ('json_ext', models.JSONField(blank=True, db_column='Json_ext', null=True)),
                ('date_created', core.fields.DateTimeField(db_column='DateCreated', default=datetime.datetime.now, null=True)),
                ('date_updated', core.fields.DateTimeField(db_column='DateUpdated', default=datetime.datetime.now, null=True)),
                ('version', models.IntegerField(default=1)),
                ('status', models.CharField(choices=[('TRIGGERED', 'Triggered'), ('IN_PROGRESS', 'In progress'), ('SUCCESS', 'Success'), ('FAIL', 'Fail')], default='TRIGGERED', max_length=255)),
                ('error', models.JSONField(blank=True, default=dict)),
                ('file_name', models.CharField(blank=True, max_length=255, null=True)),
                ('policyholder', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='policyholder.policyholder')),
                ('user_created', models.ForeignKey(db_column='UserCreatedUUID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_user_created', to=settings.AUTH_USER_MODEL)),
                ('user_updated', models.ForeignKey(db_column='UserUpdatedUUID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_user_updated', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
            bases=(dirtyfields.dirtyfields.DirtyFieldsMixin, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalWorkerUpload',
            fields=[
                ('id', models.UUIDField(db_column='UUID', db_index=True, default=None, editable=False)),
                ('is_deleted', models.BooleanField(db_column='isDeleted', default=False)),
                ('json_ext', models.JSONField(blank=True, db_column='Json_ext', null=True)),
                ('date_created', core.fields.DateTimeField(db_column='DateCreated', default=datetime.datetime.now, null=True)),
                ('date_updated', core.fields.DateTimeField(db_column='DateUpdated', default=datetime.datetime.now, null=True)),
                ('version', models.IntegerField(default=1)),
                ('status', models.CharField(choices=[('TRIGGERED', 'Triggered'), ('IN_PROGRESS', 'In progress'), ('SUCCESS', 'Success'), ('FAIL', 'Fail')], default='TRIGGERED', max_length=255)),
                ('error', models.JSONField(blank=True, default=dict)),
                ('file_name', models.CharField(blank=True, max_length=255, null=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('policyholder', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='policyholder.policyholder')),
                ('user_created', models.ForeignKey(blank=True, db_column='UserCreatedUUID', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('user_updated', models.ForeignKey(blank=True, db_column='UserUpdatedUUID', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'historical worker upload',
                'verbose_name_plural': 'historical worker uploads',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
