from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or reset the demo admin superuser (admin / admin)."

    def handle(self, *args, **options):
        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@example.com",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        user.email = "admin@example.com"
        user.is_staff = True
        user.is_superuser = True
        user.set_password("admin")
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS("Created demo superuser: admin / admin"))
        else:
            self.stdout.write(self.style.SUCCESS("Reset demo superuser password: admin / admin"))
