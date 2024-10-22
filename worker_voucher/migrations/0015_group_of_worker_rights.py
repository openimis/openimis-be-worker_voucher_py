from django.db import migrations

rights = ['206001', '206002', '206003', '206004']
roles = ['Employer', 'IMIS Administrator']


def add_rights(role_name, role_model, role_right_model):
    role = role_model.objects.get(name=role_name, validity_to__isnull=True)
    for right_id in rights:
        if not role_right_model.objects.filter(validity_to__isnull=True, role=role, right_id=right_id).exists():
            _add_right_for_role(role, right_id, role_right_model)


def _add_right_for_role(role, right_id, role_right_model):
    role_right_model.objects.create(role=role, right_id=right_id, audit_user_id=1)


def remove_rights(role_id, role_right_model):
    role_right_model.objects.filter(
        role__is_system=role_id,
        right_id__in=rights,
        validity_to__isnull=True
    ).delete()


def on_migration(apps, schema_editor):
    role_model = apps.get_model("core", "role")
    role_right_model = apps.get_model("core", "roleright")
    for role in roles:
        add_rights(role, role_model, role_right_model)


def on_reverse_migration(apps, schema_editor):
    role_right_model = apps.get_model("core", "roleright")
    for role in roles:
        remove_rights(role, role_right_model)


class Migration(migrations.Migration):
    dependencies = [
        ('worker_voucher', '0014_alter_groupofworker_name_and_more'),
    ]

    operations = [
        migrations.RunPython(on_migration, on_reverse_migration),
    ]
