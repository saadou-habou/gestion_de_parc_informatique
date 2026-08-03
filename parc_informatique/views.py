from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.timezone import now

from parc_informatique.forms import (
    AffectationForm,
    AppareilForm,
    HistoriqueMaintenanceForm,
    ModificationAppareilForm,
)
from parc_informatique.models import Appareil, HistoriqueAffectation, HistoriqueMaintenance, Utilisateur


PARC_INFORMATIQUE_INDEX = "parc_informatique:index"

APPAREILS_PAR_PAGE = 10
UTILISATEURS_PAR_PAGE = 10
MAINTENANCES_PAR_PAGE = 10


def dashboard(request):
    appareils = Appareil.objects.all()
    context = {
        "total_appareils": appareils.count(),
        "appareils_disponibles": appareils.filter(etat="Disponible").count(),
        "appareils_maintenance": appareils.filter(etat="En réparation").count(),
        "appareils_obsoletes": appareils.filter(etat="Obsolète").count(),
        "appareils_affectes": appareils.exclude(utilisateur__isnull=True).count(),
        "utilisateurs_actifs": Utilisateur.objects.filter(appareils__isnull=False).distinct().count(),
        "appareils_en_alerte": appareils.filter(etat="En réparation").order_by("nom")[:5],
        "dernieres_activites": HistoriqueMaintenance.objects.select_related("appareil")
                                    .order_by("-date_intervention")[:6],
    }
    return render(request, "parc_informatique/dashboard.html", context)


def index(request):
    appareils_list = Appareil.objects.all().order_by("nom")
    paginator = Paginator(appareils_list, APPAREILS_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "appareils": page_obj,          # itérable : {% for appareil in appareils %} fonctionne toujours
        "page_obj": page_obj,
        "total_appareils": paginator.count,
    }
    return render(request, "parc_informatique/index.html", context)


def afficher_appareil(request, appareil_id):
    context = {
        "appareil": get_object_or_404(Appareil, pk=appareil_id),
        "local": Appareil.localisation,
    }
    return render(request, "parc_informatique/afficher_appareil.html", context)


def ajouter_appareil(request):
    if request.method == "POST":
        form = AppareilForm(request.POST)

        if form.is_valid():
            appareil = form.save()
            # Si l'appareil est créé avec un utilisateur déjà renseigné,
            # on ouvre la toute première ligne d'historique d'affectation.
            if appareil.utilisateur:
                HistoriqueAffectation.objects.create(
                    appareil=appareil,
                    utilisateur=appareil.utilisateur,
                    date_debut=appareil.date_acquisition or now().date(),
                )
            return redirect(PARC_INFORMATIQUE_INDEX)
    else:
        form = AppareilForm()
    context = {"form": form}
    return render(request, "parc_informatique/appareil-form.html", context)


def modifier_appareil(request, appareil_id):
    appareil = Appareil.objects.get(pk=appareil_id)
    if request.method == "POST":
        form = ModificationAppareilForm(request.POST, instance=appareil)

        if form.is_valid():
            form.save()
            return redirect(PARC_INFORMATIQUE_INDEX)
    else:
        form = ModificationAppareilForm(instance=appareil)

    return render(request, "parc_informatique/appareil_edit_form.html", {"form": form})


def supprimer_appareil(request, appareil_id):
    appareil = Appareil.objects.get(pk=appareil_id)
    if request.method == "POST":
        appareil.delete()
        return redirect(PARC_INFORMATIQUE_INDEX)
    return render(request, "parc_informatique/confirmer_suppression.html", {"appareil": appareil})


def historique_maintenance(request, appareil_id):
    appareil = get_object_or_404(Appareil, pk=appareil_id)
    maintenances = HistoriqueMaintenance.objects.filter(appareil=appareil).order_by('-date_intervention')
    context = {
        "appareil": appareil,
        "historiquemaintenances": maintenances,
    }
    return render(request, "parc_informatique/historique_maintenance.html", context)


def envoyer_en_maintenance(request, appareil_id):
    appareil = get_object_or_404(Appareil, pk=appareil_id)

    if request.method == "POST":
        form = HistoriqueMaintenanceForm(request.POST)
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.appareil = appareil
            maintenance.date_intervention = now().date()
            appareil.etat = "En réparation"
            appareil.save()
            maintenance.save()
            return redirect("parc_informatique:afficher_appareil", appareil_id=appareil.id)
    else:
        form = HistoriqueMaintenanceForm()

    return render(request, "parc_informatique/envoyer_en_maintenance.html", {"form": form, "appareil": appareil})


# ---------------------------------------------------------------------------
# Utilisateurs & affectations
# ---------------------------------------------------------------------------

def liste_utilisateurs(request):
    utilisateurs_list = Utilisateur.objects.all().order_by("nom", "prenom")
    paginator = Paginator(utilisateurs_list, UTILISATEURS_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "utilisateurs": page_obj,
        "page_obj": page_obj,
        "total_utilisateurs": paginator.count,
    }
    return render(request, "parc_informatique/utilisateurs_liste.html", context)


def profil_utilisateur(request, utilisateur_id):
    utilisateur = get_object_or_404(Utilisateur, pk=utilisateur_id)
    appareils_affectes = Appareil.objects.filter(utilisateur=utilisateur).order_by("nom")
    historique_affectations = (
        HistoriqueAffectation.objects.filter(utilisateur=utilisateur)
        .select_related("appareil")
        .order_by("-date_debut")
    )
    context = {
        "utilisateur": utilisateur,
        "appareils_affectes": appareils_affectes,
        "historique_affectations": historique_affectations,
    }
    return render(request, "parc_informatique/utilisateur_profil.html", context)


def affecter_appareil(request, appareil_id):
    """Change l'utilisateur affecté à un appareil et historise le changement."""
    appareil = get_object_or_404(Appareil, pk=appareil_id)

    if request.method == "POST":
        form = AffectationForm(request.POST, instance=appareil)
        if form.is_valid():
            nouvel_utilisateur = form.cleaned_data["utilisateur"]
            aujourdhui = now().date()

            # Clôture l'affectation en cours (s'il y en a une) à la date du jour.
            HistoriqueAffectation.objects.filter(
                appareil=appareil, date_fin__isnull=True
            ).update(date_fin=aujourdhui)

            # Ouvre une nouvelle ligne d'historique si un utilisateur est choisi.
            if nouvel_utilisateur:
                HistoriqueAffectation.objects.create(
                    appareil=appareil,
                    utilisateur=nouvel_utilisateur,
                    date_debut=aujourdhui,
                )

            form.save()  # met à jour appareil.utilisateur
            return redirect("parc_informatique:afficher_appareil", appareil_id=appareil.id)
    else:
        form = AffectationForm(instance=appareil)

    return render(
        request,
        "parc_informatique/affecter_appareil.html",
        {"form": form, "appareil": appareil},
    )


def historique_affectations(request, appareil_id):
    appareil = get_object_or_404(Appareil, pk=appareil_id)
    affectations = (
        HistoriqueAffectation.objects.filter(appareil=appareil)
        .select_related("utilisateur")
        .order_by("-date_debut")
    )
    context = {"appareil": appareil, "affectations": affectations}
    return render(request, "parc_informatique/historique_affectations.html", context)


# ---------------------------------------------------------------------------
# Maintenances
# ---------------------------------------------------------------------------

def liste_maintenances(request):
    """Vue globale de toutes les interventions de maintenance, tous appareils confondus."""
    maintenances_list = HistoriqueMaintenance.objects.select_related("appareil").order_by(
        "-date_intervention", "-id"
    )
    paginator = Paginator(maintenances_list, MAINTENANCES_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "maintenances": page_obj,
        "page_obj": page_obj,
        "total_maintenances": paginator.count,
        "maintenances_en_cours": HistoriqueMaintenance.objects.filter(statut="Non réparé").count(),
        "maintenances_terminees": HistoriqueMaintenance.objects.filter(statut="Réparé").count(),
    }
    return render(request, "parc_informatique/maintenances_liste.html", context)


def terminer_maintenance(request, maintenance_id):
    """
    Marque une intervention comme réparée. Si l'appareil concerné n'a plus
    aucune autre maintenance "Non réparé" en cours, il repasse automatiquement
    à l'état "Disponible" (symétrique de `envoyer_en_maintenance`, qui le
    faisait passer à "En réparation").
    """
    maintenance = get_object_or_404(HistoriqueMaintenance, pk=maintenance_id)

    if request.method == "POST":
        maintenance.statut = "Réparé"
        maintenance.save()

        appareil = maintenance.appareil
        maintenances_ouvertes = HistoriqueMaintenance.objects.filter(
            appareil=appareil, statut="Non réparé"
        ).exclude(pk=maintenance.pk)
        if appareil.etat == "En réparation" and not maintenances_ouvertes.exists():
            appareil.etat = "Disponible"
            appareil.save()

    next_url = request.POST.get("next") or request.GET.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return redirect(next_url)
    return redirect("parc_informatique:liste_maintenances")
