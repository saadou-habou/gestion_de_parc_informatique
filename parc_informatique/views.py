from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.timezone import now

from parc_informatique.forms import AppareilForm, HistoriqueMaintenanceForm, ModificationAppareilForm
from parc_informatique.models import Appareil, HistoriqueMaintenance, Utilisateur


PARC_INFORMATIQUE_INDEX = "parc_informatique:index"

APPAREILS_PAR_PAGE = 10
UTILISATEURS_PAR_PAGE = 10


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
            form.save()
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
    context = {
        "utilisateur": utilisateur,
        "appareils_affectes": appareils_affectes,
    }
    return render(request, "parc_informatique/utilisateur_profil.html", context)
