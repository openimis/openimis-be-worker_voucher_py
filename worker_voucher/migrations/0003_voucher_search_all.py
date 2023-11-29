from django.db import migrations

rights = ['204002', '204003', '204004', '204005']
roles = ['Inspector', 'IMIS Administrator']


def add_rights(role_name, role_model, role_right_model):
    role = role_model.objects.get(name=role_name)
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
        ('worker_voucher', '0002_voucher_rights'),
    ]

    operations = [
        migrations.RunPython(on_migration, on_reverse_migration),
    ]
