from django.db import migrations


def seed_initial_roles(apps, schema_editor):
    Role = apps.get_model("users", "Role")

    # Seed only the first two supported roles so the registration form works
    # immediately after migrate while still leaving room for future roles.
    initial_roles = [
        {
            "slug": "farmer",
            "name": "Farmer",
            "dashboard_namespace": "farmers_dashboard",
            "default_path": "/farmers/",
        },
        {
            "slug": "veterinary",
            "name": "Veterinary",
            "dashboard_namespace": "veterinary_dashboard",
            "default_path": "/veterinary/",
        },
    ]

    for payload in initial_roles:
        Role.objects.update_or_create(
            slug=payload["slug"],
            defaults=payload,
        )


def unseed_initial_roles(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Role.objects.filter(slug__in=["farmer", "veterinary"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_initial_roles, unseed_initial_roles),
    ]
