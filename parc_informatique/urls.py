from django.contrib.auth import views as auth_views
from django.urls import path
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

    path("", views.index, name='index'),  # inchangé : liste des appareils reste à la racine
    path("dashboard/", views.dashboard, name='dashboard'),  # nouveau tableau de bord
    path("appareils/<int:appareil_id>/", views.afficher_appareil, name='afficher_appareil'),
    path("ajouter-appareil/", views.ajouter_appareil, name="ajouter_appareil"),
    path("appareils/<int:appareil_id>/modifier/", views.modifier_appareil, name="modifier_appareil"),
    path("appareils/<int:appareil_id>/supprimer/", views.supprimer_appareil, name="supprimer_appareil"),
    path("appareils/<int:appareil_id>/maintenance/", views.historique_maintenance, name='historique_maintenance'),
    path("appareils/<int:appareil_id>/evoyer_en_maintenance/", views.envoyer_en_maintenance, name="envoyer_en_maintenance"),
    path("appareils/<int:appareil_id>/affecter/", views.affecter_appareil, name="affecter_appareil"),
    path("appareils/<int:appareil_id>/affectations/", views.historique_affectations, name="historique_affectations"),

    # Utilisateurs & affectations
    path("utilisateurs/", views.liste_utilisateurs, name="liste_utilisateurs"),
    path("utilisateurs/<int:utilisateur_id>/", views.profil_utilisateur, name="profil_utilisateur"),

    # Maintenances
    path("maintenances/", views.liste_maintenances, name="liste_maintenances"),
    path("maintenances/<int:maintenance_id>/terminer/", views.terminer_maintenance, name="terminer_maintenance"),

    # Techniciens
    path("techniciens/", views.liste_techniciens, name="liste_techniciens"),
    path("techniciens/ajouter/", views.ajouter_technicien, name="ajouter_technicien"),
    path("techniciens/<int:technicien_id>/modifier/", views.modifier_technicien, name="modifier_technicien"),
    path("techniciens/<int:technicien_id>/supprimer/", views.supprimer_technicien, name="supprimer_technicien"),

    # Compte
    path("compte/profil/", views.profil_compte, name="profil_compte"),
    path("compte/parametres/", views.parametres_compte, name="parametres_compte"),
]
