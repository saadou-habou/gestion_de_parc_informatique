from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy
from . import views
from .forms import BootstrapAuthenticationForm

app_name = 'parc_informatique'


urlpatterns = [
    # Authentification
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="parc_informatique/auth/login.html",
            authentication_form=BootstrapAuthenticationForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="parc_informatique:login"),
        name="logout",
    ),

    # Mot de passe oublié
    path(
        "mot-de-passe-oublie/",
        auth_views.PasswordResetView.as_view(
            template_name="parc_informatique/auth/password_reset_form.html",
            email_template_name="parc_informatique/auth/password_reset_email.txt",
            subject_template_name="parc_informatique/auth/password_reset_subject.txt",
            success_url=reverse_lazy("parc_informatique:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "mot-de-passe-oublie/envoye/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="parc_informatique/auth/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "reinitialiser/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="parc_informatique/auth/password_reset_confirm.html",
            success_url=reverse_lazy("parc_informatique:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "reinitialiser/termine/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="parc_informatique/auth/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),

    path("", views.index, name='index'),  # inchangé : liste des appareils reste à la racine
    path("dashboard/", views.dashboard, name='dashboard'),  # nouveau tableau de bord
    path("recherche/", views.recherche_globale, name="recherche_globale"),
    path("appareils/<int:appareil_id>/", views.afficher_appareil, name='afficher_appareil'),
    path("ajouter-appareil/", views.ajouter_appareil, name="ajouter_appareil"),
    path("appareils/<int:appareil_id>/modifier/", views.modifier_appareil, name="modifier_appareil"),
    path("appareils/<int:appareil_id>/supprimer/", views.supprimer_appareil, name="supprimer_appareil"),
    path("appareils/<int:appareil_id>/maintenance/", views.historique_maintenance, name='historique_maintenance'),
    path("appareils/<int:appareil_id>/evoyer_en_maintenance/", views.envoyer_en_maintenance, name="envoyer_en_maintenance"),
    path("appareils/<int:appareil_id>/affecter/", views.affecter_appareil, name="affecter_appareil"),
    path("appareils/<int:appareil_id>/affectations/", views.historique_affectations, name="historique_affectations"),
    path("appareils/<int:appareil_id>/qrcode/", views.qr_code_appareil, name="qr_code_appareil"),
    path("appareils/exporter/", views.export_appareils_csv, name="export_appareils_csv"),
    path("appareils/importer/", views.importer_appareils, name="importer_appareils"),

    # Utilisateurs & affectations
    path("utilisateurs/", views.liste_utilisateurs, name="liste_utilisateurs"),
    path("utilisateurs/ajouter/", views.ajouter_utilisateur, name="ajouter_utilisateur"),
    path("utilisateurs/<int:utilisateur_id>/", views.profil_utilisateur, name="profil_utilisateur"),
    path("utilisateurs/<int:utilisateur_id>/modifier/", views.modifier_utilisateur, name="modifier_utilisateur"),
    path("utilisateurs/<int:utilisateur_id>/supprimer/", views.supprimer_utilisateur, name="supprimer_utilisateur"),

    # Locaux
    path("locaux/", views.liste_locaux, name="liste_locaux"),
    path("locaux/ajouter/", views.ajouter_local, name="ajouter_local"),
    path("locaux/<int:local_id>/modifier/", views.modifier_local, name="modifier_local"),
    path("locaux/<int:local_id>/supprimer/", views.supprimer_local, name="supprimer_local"),

    # Maintenances
    path("maintenances/", views.liste_maintenances, name="liste_maintenances"),
    path("maintenances/<int:maintenance_id>/terminer/", views.terminer_maintenance, name="terminer_maintenance"),
    path("maintenances/exporter/", views.export_maintenances_csv, name="export_maintenances_csv"),
    path("mes-interventions/", views.mes_interventions, name="mes_interventions"),

    # Techniciens
    path("techniciens/", views.liste_techniciens, name="liste_techniciens"),
    path("techniciens/ajouter/", views.ajouter_technicien, name="ajouter_technicien"),
    path("techniciens/<int:technicien_id>/modifier/", views.modifier_technicien, name="modifier_technicien"),
    path("techniciens/<int:technicien_id>/supprimer/", views.supprimer_technicien, name="supprimer_technicien"),

    # Compte
    path("compte/profil/", views.profil_compte, name="profil_compte"),
    path("compte/parametres/", views.parametres_compte, name="parametres_compte"),

    # Notifications
    path("notifications/", views.notifications_liste, name="notifications_liste"),
    path("notifications/marquer-lues/", views.marquer_notifications_lues, name="marquer_notifications_lues"),

    # Statistiques & audit
    path("statistiques/", views.statistiques, name="statistiques"),
    path("journal-audit/", views.liste_journal_audit, name="liste_journal_audit"),
]
