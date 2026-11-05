"""Services métier transactionnels pour le cycle de vie des maintenances."""

from django.db import transaction
from django.utils.timezone import localdate

from parc_informatique.models import Appareil, HistoriqueMaintenance


@transaction.atomic
def ouvrir_maintenance(*, appareil_id, description, technicien=None, cout=None, date_intervention=None):
    """Ouvre une intervention et synchronise l'état de l'appareil dans une transaction."""
    appareil = Appareil.objects.select_for_update().get(pk=appareil_id)
    maintenance = HistoriqueMaintenance.objects.create(
        appareil=appareil,
        date_intervention=date_intervention or localdate(),
        description=description,
        technicien=technicien,
        cout=cout,
        statut="Non réparé",
    )
    if appareil.etat != "En réparation":
        appareil.etat = "En réparation"
        appareil.save(update_fields=["etat"])
    return maintenance


@transaction.atomic
def terminer_maintenance(*, maintenance_id, date_reparation=None):
    """Clôture une intervention et libère l'appareil seulement si aucune autre ne reste ouverte."""
    maintenance = (
        HistoriqueMaintenance.objects.select_for_update()
        .select_related("appareil")
        .get(pk=maintenance_id)
    )
    if maintenance.statut != "Réparé" or maintenance.date_reparation is None:
        maintenance.statut = "Réparé"
        maintenance.date_reparation = date_reparation or localdate()
        maintenance.save(update_fields=["statut", "date_reparation"])

    appareil = Appareil.objects.select_for_update().get(pk=maintenance.appareil_id)
    autre_ouverte = HistoriqueMaintenance.objects.filter(
        appareil_id=appareil.pk, statut="Non réparé"
    ).exclude(pk=maintenance.pk).exists()
    if appareil.etat == "En réparation" and not autre_ouverte:
        appareil.etat = "Disponible"
        appareil.save(update_fields=["etat"])
    return maintenance


@transaction.atomic
def changer_etat_appareil(*, appareil_id, nouvel_etat):
    """Change l'état opérationnel sans laisser d'interventions ouvertes orphelines."""
    if nouvel_etat not in dict(Appareil.ETAT_CHOICES):
        raise ValueError("État d'appareil invalide.")

    appareil = Appareil.objects.select_for_update().get(pk=appareil_id)
    if appareil.etat == nouvel_etat:
        return appareil
    if nouvel_etat == "En réparation":
        raise ValueError("Pour envoyer un appareil en réparation, il faut ouvrir une intervention.")

    if appareil.etat == "En réparation":
        HistoriqueMaintenance.objects.filter(
            appareil_id=appareil.pk, statut="Non réparé"
        ).update(statut="Réparé", date_reparation=localdate())

    appareil.etat = nouvel_etat
    appareil.save(update_fields=["etat"])
    return appareil
