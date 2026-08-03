"""
Commande de rétro-remplissage : crée une ligne HistoriqueAffectation "en cours"
pour chaque appareil déjà affecté à un utilisateur au moment où cette
fonctionnalité est activée, afin de ne pas perdre l'affectation actuelle.

Usage :
    python manage.py backfill_affectations
"""
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from parc_informatique.models import Appareil, HistoriqueAffectation


class Command(BaseCommand):
    help = "Crée une entrée d'historique d'affectation pour les appareils déjà affectés."

    def handle(self, *args, **options):
        appareils_affectes = Appareil.objects.exclude(utilisateur__isnull=True)
        crees = 0

        for appareil in appareils_affectes:
            deja_historise = HistoriqueAffectation.objects.filter(
                appareil=appareil, utilisateur=appareil.utilisateur, date_fin__isnull=True
            ).exists()
            if deja_historise:
                continue

            HistoriqueAffectation.objects.create(
                appareil=appareil,
                utilisateur=appareil.utilisateur,
                date_debut=appareil.date_acquisition or now().date(),
            )
            crees += 1

        self.stdout.write(self.style.SUCCESS(
            f"{crees} entrée(s) d'historique d'affectation créée(s) sur {appareils_affectes.count()} appareil(s) affecté(s)."
        ))
