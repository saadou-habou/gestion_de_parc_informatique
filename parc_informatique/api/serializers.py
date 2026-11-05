from django.db import transaction
from rest_framework import serializers

from parc_informatique.models import (
    Appareil,
    HistoriqueAffectation,
    HistoriqueMaintenance,
    Local,
    Technicien,
    Utilisateur,
)


class LocalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Local
        fields = ["id", "nom", "etage", "batiment"]


class UtilisateurSerializer(serializers.ModelSerializer):
    class Meta:
        model = Utilisateur
        fields = ["id", "nom", "prenom", "email", "telephone", "poste"]


class TechnicienSerializer(serializers.ModelSerializer):
    class Meta:
        model = Technicien
        fields = ["id", "nom", "prenom", "email", "telephone", "specialite", "actif", "compte_utilisateur"]


class AppareilSerializer(serializers.ModelSerializer):
    localisation_nom = serializers.CharField(
        source="localisation.nom", read_only=True, default=None
    )
    utilisateur_nom = serializers.SerializerMethodField()
    garantie_expiree = serializers.BooleanField(read_only=True)

    class Meta:
        model = Appareil
        fields = [
            "id", "nom", "type", "marque", "modele", "numero_serie", "etat",
            "date_acquisition", "fournisseur", "prix_achat", "date_fin_garantie",
            "garantie_expiree", "localisation", "localisation_nom",
            "utilisateur", "utilisateur_nom",
        ]
        # Les écritures d'affectation et d'état sont redirigées vers les services
        # métier afin de conserver l'historique et les invariants.

    def get_utilisateur_nom(self, obj):
        return str(obj.utilisateur) if obj.utilisateur_id else None

    def validate_etat(self, value):
        if value == "En réparation" and (
            self.instance is None or self.instance.etat != "En réparation"
        ):
            raise serializers.ValidationError(
                "Utilisez la création d'une maintenance pour passer un appareil en réparation."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        utilisateur = validated_data.pop("utilisateur", None)
        appareil = super().create(validated_data)
        if utilisateur is not None:
            from parc_informatique.services.assignments import changer_affectation

            appareil, _ = changer_affectation(appareil_id=appareil.pk, utilisateur=utilisateur)
        return appareil

    @transaction.atomic
    def update(self, instance, validated_data):
        nouvel_etat = validated_data.pop("etat", None)
        utilisateur = validated_data.pop("utilisateur", serializers.empty)
        if nouvel_etat is not None:
            from parc_informatique.services.maintenance import changer_etat_appareil

            instance = changer_etat_appareil(appareil_id=instance.pk, nouvel_etat=nouvel_etat)
        if utilisateur is not serializers.empty:
            from parc_informatique.services.assignments import changer_affectation

            instance, _ = changer_affectation(appareil_id=instance.pk, utilisateur=utilisateur)
        return super().update(instance, validated_data)


class HistoriqueMaintenanceSerializer(serializers.ModelSerializer):
    appareil_nom = serializers.CharField(source="appareil.nom", read_only=True)
    technicien_nom = serializers.SerializerMethodField()

    class Meta:
        model = HistoriqueMaintenance
        fields = [
            "id", "appareil", "appareil_nom", "date_intervention", "date_reparation",
            "description", "technicien", "technicien_nom", "statut", "cout",
        ]
        # La date d'intervention est fixée côté serveur à la création (comme sur
        # le site) ; date_reparation n'est renseignée que par l'action "terminer".
        read_only_fields = ["date_intervention", "date_reparation", "statut"]

    def get_fields(self):
        fields = super().get_fields()
        # L'appareil est fourni à la création, mais une intervention existante
        # ne peut pas être déplacée vers un autre appareil par PATCH/PUT.
        if self.instance is not None:
            fields["appareil"].read_only = True
        return fields

    def get_technicien_nom(self, obj):
        return str(obj.technicien) if obj.technicien_id else None

    def create(self, validated_data):
        from parc_informatique.services.maintenance import ouvrir_maintenance

        return ouvrir_maintenance(
            appareil_id=validated_data["appareil"].pk,
            description=validated_data["description"],
            technicien=validated_data.get("technicien"),
            cout=validated_data.get("cout"),
        )


class HistoriqueAffectationSerializer(serializers.ModelSerializer):
    appareil_nom = serializers.CharField(source="appareil.nom", read_only=True)
    utilisateur_nom = serializers.SerializerMethodField()

    class Meta:
        model = HistoriqueAffectation
        fields = ["id", "appareil", "appareil_nom", "utilisateur", "utilisateur_nom", "date_debut", "date_fin"]
        read_only_fields = fields  # historique en lecture seule via l'API pour l'instant

    def get_utilisateur_nom(self, obj):
        return str(obj.utilisateur) if obj.utilisateur_id else None
