from django.core.cache import cache
from django.db.models import Exists, OuterRef

from parc_informatique.models import Notification
from parc_informatique.notifications import generer_notifications
from parc_informatique.roles import ADMIN, GESTIONNAIRE, TECHNICIEN, roles_de


def roles_context(request):
    """
    Expose les rôles de l'utilisateur connecté à tous les templates, pour
    masquer/afficher des liens (ex. la sidebar) selon le rôle, sans dupliquer
    la logique de rôles dans chaque vue.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    roles = roles_de(user)
    return {
        "roles_utilisateur": roles,
        "role_principal": (
            ADMIN if ADMIN in roles else
            GESTIONNAIRE if GESTIONNAIRE in roles else
            TECHNICIEN if TECHNICIEN in roles else
            None
        ),
        "est_admin": ADMIN in roles,
        "est_gestionnaire": bool(roles & {ADMIN, GESTIONNAIRE}),
        "est_technicien_role": TECHNICIEN in roles,
    }


def notifications_context(request):
    """
    Expose les notifications actives à la navbar. La génération, qui écrit
    en base, est limitée à une exécution toutes les cinq minutes par cache ;
    en production, privilégier la commande `generer_notifications` planifiée
    et un cache partagé entre workers.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    # Le calcul écrit en base : ne pas le relancer à chaque rendu de page.
    # Le management command `generer_notifications` reste disponible pour cron.
    if cache.add("parc_informatique:notifications:last_generation", True, timeout=300):
        generer_notifications()

    notifications_actives = (
        Notification.objects.filter(resolue=False)
        .annotate(lue=Exists(Notification.objects.filter(pk=OuterRef("pk"), lue_par=user)))
        .order_by("-cree_le")
    )

    return {
        "notifications_recentes": notifications_actives[:8],
        "notifications_non_lues_count": notifications_actives.filter(lue=False).count(),
    }
