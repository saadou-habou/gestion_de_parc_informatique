from django.contrib import admin

from parc_informatique.models import (
    Appareil,
    HistoriqueAffectation,
    HistoriqueMaintenance,
    JournalAudit,
    Local,
    Notification,
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
    list_display = ("nom", "prenom", "specialite", "email", "telephone", "actif", "compte_utilisateur")
    list_filter = ("actif", "specialite")
    search_fields = ("nom", "prenom", "email")
    autocomplete_fields = ("compte_utilisateur",)


@admin.register(Appareil)
class AppareilAdmin(admin.ModelAdmin):
    list_display = (
        "nom", "type", "marque", "modele", "numero_serie", "etat",
        "utilisateur", "localisation", "fournisseur", "prix_achat", "date_fin_garantie",
    )
    list_filter = ("type", "etat")
    search_fields = ("nom", "numero_serie", "marque", "modele", "fournisseur")
    autocomplete_fields = ("localisation", "utilisateur")


@admin.register(HistoriqueMaintenance)
class HistoriqueMaintenanceAdmin(admin.ModelAdmin):
    list_display = ("appareil", "date_intervention", "date_reparation", "technicien", "statut", "cout")
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


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("message", "type", "niveau", "appareil", "resolue", "cree_le")
    list_filter = ("type", "niveau", "resolue")
    search_fields = ("message", "appareil__nom")
    readonly_fields = ("cle_naturelle", "cree_le", "resolue_le")


@admin.register(JournalAudit)
class JournalAuditAdmin(admin.ModelAdmin):
    list_display = ("horodatage", "utilisateur", "action", "modele", "objet_repr")
    list_filter = ("action", "modele")
    search_fields = ("objet_repr", "details", "utilisateur__username")
    readonly_fields = ("horodatage", "utilisateur", "action", "modele", "objet_repr", "details")

    def has_add_permission(self, request):
        return False  # journal généré uniquement par l'application, jamais saisi à la main

    def has_change_permission(self, request, obj=None):
        return False
