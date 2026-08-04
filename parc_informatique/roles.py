"""
Logique de rôles, centralisée ici et partagée par :
- les vues Django classiques (décorateur `role_required` dans decorators.py) ;
- l'API DRF/JWT (permissions dans api/permissions.py).

On s'appuie sur les Groups Django natifs plutôt que sur un champ `role`
personnalisé : ça reste gérable directement depuis /admin/ (déjà en place),
sans modèle ni migration supplémentaire.
"""

ADMIN = "Admin"
GESTIONNAIRE = "Gestionnaire"
TECHNICIEN = "Technicien"

TOUS_LES_ROLES = (ADMIN, GESTIONNAIRE, TECHNICIEN)

# Rôles autorisés à créer/modifier/supprimer des appareils, utilisateurs,
# techniciens et affectations.
ROLES_GESTION = (ADMIN, GESTIONNAIRE)


def roles_de(user):
    """Renvoie l'ensemble des rôles (noms de Group) d'un utilisateur.
    Un superuser Django est considéré comme ayant tous les rôles."""
    if not user or not getattr(user, "is_authenticated", False):
        return set()
    if user.is_superuser:
        return set(TOUS_LES_ROLES)
    return set(user.groups.values_list("name", flat=True)) & set(TOUS_LES_ROLES)


def a_un_role_parmi(user, *roles_autorises):
    return bool(roles_de(user) & set(roles_autorises))


def role_principal(user):
    """Le rôle "le plus élevé" d'un utilisateur, pour l'affichage (badge, etc.)."""
    roles = roles_de(user)
    for role in (ADMIN, GESTIONNAIRE, TECHNICIEN):
        if role in roles:
            return role
    return None
