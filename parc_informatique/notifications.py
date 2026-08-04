"""
Génère les notifications à partir de règles métier. Idempotent : peut être
appelé à chaque requête (via le context processor) ou depuis une tâche
planifiée (`python manage.py generer_notifications`) sans jamais créer de
doublon — chaque événement a une `cle_naturelle` stable, et un événement qui
n'est plus d'actualité est automatiquement marqué "résolu" plutôt que
supprimé (pour garder un historique consultable).
"""

from datetime import timedelta

from django.urls import reverse
from django.utils.timezone import now

from parc_informatique.models import Appareil, HistoriqueMaintenance, Notification

# Nombre de jours au-delà desquels une maintenance "Non réparé" déclenche une alerte.
MAINTENANCE_RETARD_JOURS = 3


def generer_notifications():
    cles_actives = set()

    _generer_maintenances_en_retard(cles_actives)
    _generer_appareils_obsoletes(cles_actives)

    # Toute notification active dont la clé n'est plus dans le lot calculé
    # ci-dessus correspond à un événement résolu (maintenance terminée,
    # appareil réintégré...).
    Notification.objects.filter(resolue=False).exclude(cle_naturelle__in=cles_actives).update(
        resolue=True, resolue_le=now()
    )


def _generer_maintenances_en_retard(cles_actives):
    seuil = now().date() - timedelta(days=MAINTENANCE_RETARD_JOURS)
    maintenances = HistoriqueMaintenance.objects.filter(
        statut="Non réparé", date_intervention__lte=seuil
    ).select_related("appareil")

    for maintenance in maintenances:
        cle = f"maintenance_retard:{maintenance.id}"
        cles_actives.add(cle)
        jours = (now().date() - maintenance.date_intervention).days
        Notification.objects.update_or_create(
            cle_naturelle=cle,
            defaults={
                "type": "maintenance_retard",
                "niveau": "danger",
                "message": f"Maintenance de « {maintenance.appareil.nom} » en attente depuis {jours} jours",
                "lien": reverse(
                    "parc_informatique:historique_maintenance",
                    args=[maintenance.appareil_id],
                ),
                "appareil_id": maintenance.appareil_id,
                "resolue": False,
                "resolue_le": None,
            },
        )


def _generer_appareils_obsoletes(cles_actives):
    for appareil in Appareil.objects.filter(etat="Obsolète"):
        cle = f"appareil_obsolete:{appareil.id}"
        cles_actives.add(cle)
        Notification.objects.update_or_create(
            cle_naturelle=cle,
            defaults={
                "type": "appareil_obsolete",
                "niveau": "warning",
                "message": f"« {appareil.nom} » est marqué obsolète",
                "lien": reverse("parc_informatique:afficher_appareil", args=[appareil.id]),
                "appareil_id": appareil.id,
                "resolue": False,
                "resolue_le": None,
            },
        )
