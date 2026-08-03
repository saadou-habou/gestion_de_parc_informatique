from django.db import models
from django.utils import timezone


class Local(models.Model):
    nom = models.CharField(max_length=100)
    etage = models.CharField(max_length=50, blank=True)
    batiment = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.nom} ({self.batiment}, étage {self.etage})"


class Utilisateur(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telephone = models.CharField(max_length=15, blank=True)
    poste = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.nom} {self.prenom}"


class Technicien(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    telephone = models.CharField(max_length=15, blank=True)
    specialite = models.CharField(
        max_length=100, blank=True, help_text="Ex. Hardware, Réseau, Logiciel…"
    )
    actif = models.BooleanField(
        default=True,
        help_text="Un technicien inactif n'apparaît plus dans les nouveaux formulaires "
                   "de maintenance, mais son historique d'interventions est conservé.",
    )

    class Meta:
        ordering = ["nom", "prenom"]

    def __str__(self):
        complet = f"{self.nom} {self.prenom}".strip()
        return complet if self.actif else f"{complet} (inactif)"


class Appareil(models.Model):
    ETAT_CHOICES = [
        ("Disponible", "Disponible"),
        ("En réparation", "En réparation"),
        ("Obsolète", "Obsolète"),
    ]
    TYPE_CHOICES = [
        ("Desktop", "Desktop"),
        ("Laptop", "Laptop"),
        ("Périphérique", "Périphérique"),
    ]

    nom = models.CharField(max_length=100)
    type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    marque = models.CharField(max_length=100, blank=True)
    modele = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField(max_length=100, unique=True)
    etat = models.CharField(max_length=50, choices=ETAT_CHOICES, default="Disponible")
    date_acquisition = models.DateField(blank=True, null=True)
    localisation = models.ForeignKey(
        Local, on_delete=models.SET_NULL, null=True, related_name="appareils"
    )
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appareils",
    )

    def __str__(self):
        return f"{self.nom} ({self.marque} {self.modele})"


class HistoriqueMaintenance(models.Model):
    STATUT_CHOICES = [
        ("Réparé", "Réparé"),
        ("Non réparé", "Non réparé"),
    ]

    appareil = models.ForeignKey(
        Appareil, on_delete=models.CASCADE, related_name="maintenances"
    )
    date_intervention = models.DateField()
    description = models.TextField()
    technicien = models.ForeignKey(
        Technicien,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="maintenances",
    )
    statut = models.CharField(max_length=50, choices=STATUT_CHOICES, default="Réparé")

    def __str__(self):
        return f"Maintenance de {self.appareil.nom} le {self.date_intervention}"


class HistoriqueAffectation(models.Model):
    """
    Historise chaque affectation d'un appareil à un utilisateur.
    `date_fin` vaut None tant que l'affectation est en cours ; elle est
    renseignée automatiquement dès que l'appareil est réaffecté ou retiré
    à l'utilisateur (voir la vue `affecter_appareil`).
    """

    appareil = models.ForeignKey(
        Appareil, on_delete=models.CASCADE, related_name="affectations"
    )
    utilisateur = models.ForeignKey(
        Utilisateur, on_delete=models.SET_NULL, null=True, related_name="affectations"
    )
    date_debut = models.DateField(default=timezone.now)
    date_fin = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ["-date_debut", "-id"]

    def __str__(self):
        utilisateur = self.utilisateur or "Non affecté"
        if self.date_fin:
            return f"{self.appareil.nom} → {utilisateur} ({self.date_debut} → {self.date_fin})"
        return f"{self.appareil.nom} → {utilisateur} (depuis le {self.date_debut})"

    @property
    def en_cours(self):
        return self.date_fin is None
