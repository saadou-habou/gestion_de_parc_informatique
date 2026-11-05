from rest_framework import permissions, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView


from parc_informatique.models import (
    Appareil,
    HistoriqueAffectation,
    HistoriqueMaintenance,
    Local,
    Technicien,
    Utilisateur,
)
from parc_informatique.roles import ADMIN, GESTIONNAIRE, TECHNICIEN, a_un_role_parmi, roles_de
from parc_informatique.services.assignments import changer_affectation
from parc_informatique.services.maintenance import terminer_maintenance

from .permissions import EstAuthentifieAvecRole, EstGestionnaireOuLectureSeule
from .serializers import (
    AppareilSerializer,
    HistoriqueAffectationSerializer,
    HistoriqueMaintenanceSerializer,
    LocalSerializer,
    TechnicienSerializer,
    UtilisateurSerializer,
)


class LocalViewSet(viewsets.ModelViewSet):
    queryset = Local.objects.all().order_by("nom")
    serializer_class = LocalSerializer
    permission_classes = [EstGestionnaireOuLectureSeule]


class UtilisateurViewSet(viewsets.ModelViewSet):
    queryset = Utilisateur.objects.all().order_by("nom", "prenom")
    serializer_class = UtilisateurSerializer
    permission_classes = [EstGestionnaireOuLectureSeule]


class TechnicienViewSet(viewsets.ModelViewSet):
    queryset = Technicien.objects.all().order_by("nom", "prenom")
    serializer_class = TechnicienSerializer
    permission_classes = [EstGestionnaireOuLectureSeule]




class AffectationInputSerializer(serializers.Serializer):
    utilisateur = serializers.PrimaryKeyRelatedField(
        queryset=Utilisateur.objects.all(), allow_null=True, required=True
    )


class AppareilViewSet(viewsets.ModelViewSet):
    queryset = Appareil.objects.all().order_by("nom")
    serializer_class = AppareilSerializer
    permission_classes = [EstGestionnaireOuLectureSeule]

    def get_queryset(self):
        queryset = super().get_queryset()
        etat = self.request.query_params.get("etat")
        if etat:
            queryset = queryset.filter(etat=etat)
        return queryset

    def get_permissions(self):
        if self.action == "affecter":
            return [EstGestionnaireOuLectureSeule()]
        return super().get_permissions()

    @action(detail=True, methods=["post"], url_path="affecter")
    def affecter(self, request, pk=None):
        """POST /api/v1/appareils/{id}/affecter/ avec utilisateur=<id|null>."""
        appareil = self.get_object()
        serializer = AffectationInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        appareil, _ = changer_affectation(
            appareil_id=appareil.pk,
            utilisateur=serializer.validated_data["utilisateur"],
        )
        return Response(AppareilSerializer(appareil, context=self.get_serializer_context()).data)


class HistoriqueMaintenanceViewSet(viewsets.ModelViewSet):
    """
    Lecture/création ouvertes à tout rôle connecté (un Technicien doit
    pouvoir loguer et clôturer ses propres interventions) ; suppression
    réservée à l'Admin (voir EstGestionnaireOuLectureSeule).
    """

    queryset = HistoriqueMaintenance.objects.select_related("appareil", "technicien").order_by(
        "-date_intervention", "-id"
    )
    serializer_class = HistoriqueMaintenanceSerializer

    def get_permissions(self):
        # Les techniciens peuvent déclarer une intervention et la clôturer,
        # mais ne peuvent pas réécrire arbitrairement un historique existant.
        if self.action in {"destroy", "update", "partial_update"}:
            return [EstGestionnaireOuLectureSeule()]
        return [EstAuthentifieAvecRole()]

    def get_queryset(self):
        queryset = super().get_queryset()
        statut = self.request.query_params.get("statut")
        if statut:
            queryset = queryset.filter(statut=statut)
        return queryset

    @action(detail=True, methods=["post"], url_path="terminer")
    def terminer(self, request, pk=None):
        """
        POST /api/v1/maintenances/{id}/terminer/
        Équivalent API de l'action "Terminer" du site : marque l'intervention
        réparée et repasse l'appareil "Disponible" s'il n'a plus d'autre
        maintenance ouverte.
        """
        maintenance = self.get_object()
        if (
            a_un_role_parmi(request.user, TECHNICIEN)
            and not a_un_role_parmi(request.user, ADMIN, GESTIONNAIRE)
            and (not maintenance.technicien_id or maintenance.technicien.compte_utilisateur_id != request.user.pk)
        ):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Vous ne pouvez clôturer que vos propres interventions.")
        maintenance = terminer_maintenance(maintenance_id=maintenance.pk)

        return Response(self.get_serializer(maintenance).data)


class HistoriqueAffectationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HistoriqueAffectation.objects.select_related("appareil", "utilisateur").order_by(
        "-date_debut", "-id"
    )
    serializer_class = HistoriqueAffectationSerializer
    permission_classes = [EstAuthentifieAvecRole]


class MoiView(APIView):
    """GET /api/v1/moi/ — identité + rôles de l'utilisateur du token JWT courant.
    Utile pour un client mobile/SPA qui doit savoir quoi afficher juste après connexion."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "email": request.user.email,
            "roles": sorted(roles_de(request.user)),
            "is_superuser": request.user.is_superuser,
        })
