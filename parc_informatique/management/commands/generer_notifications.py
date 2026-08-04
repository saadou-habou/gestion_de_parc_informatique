from django.core.management.base import BaseCommand

from parc_informatique.notifications import generer_notifications


class Command(BaseCommand):
    help = (
        "Recalcule les notifications à partir des règles métier "
        "(maintenances en retard, appareils obsolètes...). "
        "Idempotent : peut être planifiée en cron sans créer de doublons. "
        "Optionnelle : la génération tourne déjà à chaque requête via le "
        "context processor, cette commande sert surtout si vous préférez "
        "déporter le calcul vers une tâche planifiée plutôt qu'à chaque page."
    )

    def handle(self, *args, **options):
        generer_notifications()
        self.stdout.write(self.style.SUCCESS("Notifications synchronisées."))
