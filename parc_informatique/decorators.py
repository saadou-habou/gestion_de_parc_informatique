from functools import wraps

from django.core.exceptions import PermissionDenied

from parc_informatique.roles import a_un_role_parmi


def role_required(*roles_autorises):
    """
    Restreint une vue aux utilisateurs ayant au moins un des rôles donnés
    (voir parc_informatique/roles.py). Lève un 403 sinon — la page
    templates_root/403.html s'affiche automatiquement (hors DEBUG).

    Usage :
        @role_required(ADMIN, GESTIONNAIRE)
        def ajouter_appareil(request): ...
    """

    def decorateur(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not a_un_role_parmi(request.user, *roles_autorises):
                raise PermissionDenied(
                    "Vous n'avez pas les droits nécessaires pour effectuer cette action."
                )
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorateur
