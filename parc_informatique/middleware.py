from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse


class LoginRequiredMiddleware:
    """
    Exige une authentification pour accéder à l'application dans son
    ensemble, à l'exception de la page de connexion elle-même et des
    fichiers statiques.

    Volontairement simple (pas de permissions par rôle) : "Parc Informatique"
    est un outil interne, on protège l'ensemble de l'app derrière une seule
    connexion plutôt que de décorer chaque vue une par une avec
    @login_required — ce qui serait facile à oublier sur une nouvelle vue.
    """

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
        Détermine si la page demandée doit rester accessible sans connexion.

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
        return request.path == reverse("parc_informatique:login")
