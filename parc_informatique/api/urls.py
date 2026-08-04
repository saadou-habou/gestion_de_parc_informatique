from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from . import views

router = DefaultRouter()
router.register("appareils", views.AppareilViewSet, basename="appareil")
router.register("locaux", views.LocalViewSet, basename="local")
router.register("utilisateurs", views.UtilisateurViewSet, basename="utilisateur")
router.register("techniciens", views.TechnicienViewSet, basename="technicien")
router.register("maintenances", views.HistoriqueMaintenanceViewSet, basename="maintenance")
router.register("affectations", views.HistoriqueAffectationViewSet, basename="affectation")

urlpatterns = [
    # Authentification JWT
    path("token/", TokenObtainPairView.as_view(), name="api_token_obtain"),
    path("token/refresh/", TokenRefreshView.as_view(), name="api_token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="api_token_verify"),

    # Identité de l'utilisateur connecté (id, email, rôles)
    path("moi/", views.MoiView.as_view(), name="api_moi"),

    # Ressources métier (CRUD via le routeur DRF)
    path("", include(router.urls)),
]
