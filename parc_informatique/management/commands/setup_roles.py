from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from parc_informatique.roles import TOUS_LES_ROLES


class Command(BaseCommand):
    help = "Crée les groupes de rôles (Admin, Gestionnaire, Technicien) s'ils n'existent pas encore."

    def handle(self, *args, **options):
        crees = 0
        for nom in TOUS_LES_ROLES:
            _, created = Group.objects.get_or_create(name=nom)
            if created:
                crees += 1

        self.stdout.write(self.style.SUCCESS(
            f"{crees} groupe(s) créé(s). Assignez ensuite chaque utilisateur à un groupe "
            f"depuis /admin/ (rubrique Utilisateurs → modifier → Groups)."
        ))
