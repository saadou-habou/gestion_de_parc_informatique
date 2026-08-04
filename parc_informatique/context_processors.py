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
    Recalcule les notifications (idempotent, voir notifications.py) et
    expose les plus récentes + le nombre de non-lues à la navbar, sur
    chaque page. Pour un parc de quelques centaines d'appareils, relancer
    le calcul à chaque requête reste largement assez rapide ; si ça devient
    sensible sur un très gros parc, basculez plutôt sur
    `python manage.py generer_notifications` planifiée en cron et retirez
    l'appel ci-dessous.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

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
