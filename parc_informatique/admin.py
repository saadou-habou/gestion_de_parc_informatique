from django.contrib import admin

from parc_informatique.models import (
    Appareil,
    HistoriqueAffectation,
    HistoriqueMaintenance,
    Local,
    Technicien,
    Utilisateur,
)


@admin.register(Local)
class LocalAdmin(admin.ModelAdmin):
    list_display = ("nom", "batiment", "etage")
    search_fields = ("nom", "batiment")


@admin.register(Utilisateur)
class UtilisateurAdmin(admin.ModelAdmin):
    list_display = ("nom", "prenom", "email", "poste", "telephone")
    search_fields = ("nom", "prenom", "email")


@admin.register(Technicien)
class TechnicienAdmin(admin.ModelAdmin):
    list_display = ("nom", "prenom", "specialite", "email", "telephone", "actif")
    list_filter = ("actif", "specialite")
    search_fields = ("nom", "prenom", "email")


@admin.register(Appareil)
class AppareilAdmin(admin.ModelAdmin):
    list_display = ("nom", "type", "marque", "modele", "numero_serie", "etat", "utilisateur", "localisation")
    list_filter = ("type", "etat")
    search_fields = ("nom", "numero_serie", "marque", "modele")
    autocomplete_fields = ("localisation", "utilisateur")


@admin.register(HistoriqueMaintenance)
class HistoriqueMaintenanceAdmin(admin.ModelAdmin):
    list_display = ("appareil", "date_intervention", "technicien", "statut")
    list_filter = ("statut", "date_intervention")
    search_fields = ("appareil__nom", "description")
    autocomplete_fields = ("appareil", "technicien")


@admin.register(HistoriqueAffectation)
class HistoriqueAffectationAdmin(admin.ModelAdmin):
    list_display = ("appareil", "utilisateur", "date_debut", "date_fin", "en_cours")
    list_filter = ("date_debut", "date_fin")
    search_fields = ("appareil__nom", "utilisateur__nom", "utilisateur__prenom")
    autocomplete_fields = ("appareil", "utilisateur")

    @admin.display(boolean=True, description="En cours")
    def en_cours(self, obj):
        return obj.en_cours
