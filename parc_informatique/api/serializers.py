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

    def get_utilisateur_nom(self, obj):
        return str(obj.utilisateur) if obj.utilisateur_id else None


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
        read_only_fields = ["date_intervention", "date_reparation"]

    def get_technicien_nom(self, obj):
        return str(obj.technicien) if obj.technicien_id else None

    def create(self, validated_data):
        from django.utils.timezone import now
        validated_data["date_intervention"] = now().date()
        maintenance = super().create(validated_data)
        # Même règle métier que envoyer_en_maintenance() côté site.
        appareil = maintenance.appareil
        appareil.etat = "En réparation"
        appareil.save(update_fields=["etat"])
        return maintenance


class HistoriqueAffectationSerializer(serializers.ModelSerializer):
    appareil_nom = serializers.CharField(source="appareil.nom", read_only=True)
    utilisateur_nom = serializers.SerializerMethodField()

    class Meta:
        model = HistoriqueAffectation
        fields = ["id", "appareil", "appareil_nom", "utilisateur", "utilisateur_nom", "date_debut", "date_fin"]
        read_only_fields = fields  # historique en lecture seule via l'API pour l'instant

    def get_utilisateur_nom(self, obj):
        return str(obj.utilisateur) if obj.utilisateur_id else None
