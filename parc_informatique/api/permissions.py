"""
Permissions DRF basées sur les mêmes rôles que le site Django classique
(voir parc_informatique/roles.py) — pour ne pas dupliquer la logique de
qui-a-le-droit-de-faire-quoi entre le site et l'API.
"""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from parc_informatique.roles import ADMIN, GESTIONNAIRE, TECHNICIEN, a_un_role_parmi


class EstAuthentifieAvecRole(BasePermission):
    """Accès en lecture/écriture pour tout utilisateur ayant au moins un des
    3 rôles (Admin, Gestionnaire, Technicien). Un utilisateur JWT valide mais
    sans aucun groupe assigné n'a accès à rien : il faut lui assigner un rôle
    depuis /admin/ (Groups)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and a_un_role_parmi(request.user, ADMIN, GESTIONNAIRE, TECHNICIEN)
        )


class EstGestionnaireOuLectureSeule(BasePermission):
    """Mêmes règles que le site :
    - lecture (GET/HEAD/OPTIONS) : tout utilisateur ayant un rôle ;
    - création / modification (POST/PUT/PATCH) : Admin ou Gestionnaire ;
    - suppression (DELETE) : Admin uniquement (sur le site, seuls les Admin
      ont accès aux vues de suppression ; l'API ne doit pas être une porte
      dérobée pour contourner cette règle)."""

    def has_permission(self, request, view):
        if not EstAuthentifieAvecRole().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return a_un_role_parmi(request.user, ADMIN)
        return a_un_role_parmi(request.user, ADMIN, GESTIONNAIRE)


class EstAdmin(BasePermission):
    """Réservé aux Admin (ou superuser)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and a_un_role_parmi(request.user, ADMIN)
        )
