from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.urls import Resolver404, resolve


class LoginRequiredMiddleware:
    """
    Exige une authentification pour accéder à l'application dans son
    ensemble, à l'exception de la page de connexion elle-même et des
    fichiers statiques.

    Volontairement simple (pas de permissions par rôle) : "Parc Informatique"
    est un outil interne, on protège l'ensemble de l'app derrière une seule
    connexion plutôt que de décorer chaque vue une par une avec
    @login_required — ce qui serait facile à oublier sur une nouvelle vue.

    Les routes /api/ sont volontairement exemptées : elles sont
    authentifiées par JWT (voir parc_informatique/api/), pas par le cookie
    de session Django que ce middleware vérifie. C'est DRF (via
    JWTAuthentication + les classes de permission) qui protège l'API, pas
    ce middleware.
    """

    # Préfixe des routes API, exemptées de la connexion par session
    # (protégées à la place par JWT — voir parc_informatique/api/).
    API_URL_PREFIX = "/api/"

    # Vues accessibles sans être connecté : la connexion elle-même et tout le
    # parcours "mot de passe oublié" (par définition utilisé par quelqu'un qui
    # ne peut PAS se connecter).
    VUES_PUBLIQUES = {
        "parc_informatique:login",
        "parc_informatique:password_reset",
        "parc_informatique:password_reset_done",
        "parc_informatique:password_reset_confirm",
        "parc_informatique:password_reset_complete",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated and not self._est_exempte(request):
            return redirect_to_login(
                request.get_full_path(), login_url=settings.LOGIN_URL
            )
        return self.get_response(request)

    def _est_exempte(self, request):
        """
        Détermine si la page demandée doit rester accessible sans connexion
        par session (l'API a son propre mécanisme d'authentification, JWT).

        Important : on ne peut PAS se baser sur `request.resolver_match` ici.
        Cet attribut n'est peuplé par Django qu'à l'intérieur de
        `self.get_response(request)`, donc à ce stade du middleware il vaut
        toujours `None` — ce qui faisait passer la page de connexion
        elle-même pour "non exemptée" et provoquait une boucle de
        redirection infinie sur /login/. On compare donc directement le
        chemin de la requête à l'URL réelle de la page de connexion.
        """
        if request.path.startswith(settings.STATIC_URL):
            return True
        if request.path.startswith(self.API_URL_PREFIX):
            return True
        # resolve() est appelable directement ici (contrairement à
        # request.resolver_match, pas encore renseigné) : on retrouve le nom
        # de la vue à partir du chemin, ce qui couvre aussi les URLs à
        # paramètres comme /reinitialiser/<uidb64>/<token>/.
        try:
            correspondance = resolve(request.path_info)
        except Resolver404:
            return False
        return correspondance.view_name in self.VUES_PUBLIQUES
