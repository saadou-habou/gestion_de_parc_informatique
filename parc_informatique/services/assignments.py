"""Services métier transactionnels pour les affectations d'équipements."""

from django.db import transaction
from django.utils.timezone import localdate

from parc_informatique.models import Appareil, HistoriqueAffectation


@transaction.atomic
def changer_affectation(*, appareil_id, utilisateur, date_debut=None):
    """Synchronise l'affectation courante et son historique, sans doublon inutile."""
    appareil = Appareil.objects.select_for_update().get(pk=appareil_id)
    if appareil.utilisateur_id == getattr(utilisateur, "pk", None):
        return appareil, False

    date_effet = date_debut or localdate()
    HistoriqueAffectation.objects.filter(
        appareil_id=appareil.pk, date_fin__isnull=True
    ).update(date_fin=date_effet)

    if utilisateur is not None:
        HistoriqueAffectation.objects.create(
            appareil=appareil, utilisateur=utilisateur, date_debut=date_effet
        )

    appareil.utilisateur = utilisateur
    appareil.save(update_fields=["utilisateur"])
    return appareil, True
