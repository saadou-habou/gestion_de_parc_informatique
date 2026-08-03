from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from parc_informatique.models import Appareil, HistoriqueMaintenance, Local, Technicien, Utilisateur


class BootstrapFieldsMixin:
    """
    Applique automatiquement les classes Bootstrap 5 (form-control /
    form-select / form-check-input) à chaque champ d'un formulaire, qu'il
    s'agisse d'un ModelForm ou d'un formulaire natif de Django (connexion,
    changement de mot de passe…).

    Sans ça, seuls les champs dont le widget est explicitement personnalisé
    reçoivent une classe CSS : tous les autres (générés automatiquement par
    Django, ex. les <select> issus des `choices`) sont rendus avec le style
    par défaut du navigateur, ce qui casse visuellement la page au milieu du
    reste de l'interface stylée. C'était le problème sur la page
    "Ajouter un appareil".
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            classes = widget.attrs.get("class", "").split()

            if isinstance(widget, forms.CheckboxInput):
                base_class = "form-check-input"
            elif isinstance(widget, (forms.Select, forms.SelectMultiple)):
                base_class = "form-select"
            else:
                base_class = "form-control"

            if base_class not in classes:
                classes.append(base_class)
            widget.attrs["class"] = " ".join(classes)


class BootstrapModelForm(BootstrapFieldsMixin, forms.ModelForm):
    pass


class BootstrapAuthenticationForm(BootstrapFieldsMixin, AuthenticationForm):
    """Formulaire de connexion (django.contrib.auth) stylé Bootstrap."""
    pass


class BootstrapPasswordChangeForm(BootstrapFieldsMixin, PasswordChangeForm):
    """Formulaire de changement de mot de passe, utilisé dans "Paramètres"."""
    pass


class AppareilForm(BootstrapModelForm):
    class Meta:
        model = Appareil
        fields = [
            'nom',
            'type',
            'marque',
            'modele',
            'numero_serie',
            'etat',
            'date_acquisition',
            'localisation',
            'utilisateur',
        ]
        labels = {
            'nom': 'Nom',
            'type': 'Type',
            'marque': 'Marque',
            'modele': 'Modèle',
            'numero_serie': 'Numéro de série',
            'etat': 'Etat',
            'date_acquisition': "Date d'acquisition",
            'localisation': 'Localisation',
            'utilisateur': 'Utilisateur',
        }
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Ex. PC-Comptabilité-01"}),
            "marque": forms.TextInput(attrs={"placeholder": "Ex. Dell, HP, Lenovo…"}),
            "modele": forms.TextInput(attrs={"placeholder": "Ex. Latitude 5540"}),
            "numero_serie": forms.TextInput(attrs={"placeholder": "Numéro de série constructeur"}),
            "date_acquisition": forms.DateInput(attrs={"type": "date"}),
        }


class ModificationAppareilForm(BootstrapModelForm):
    class Meta:
        model = Appareil
        fields = ['etat']
        labels = {'etat': 'Etat'}


class HistoriqueMaintenanceForm(BootstrapModelForm):
    class Meta:
        model = HistoriqueMaintenance
        fields = ["date_intervention", "description", "technicien", "statut"]
        labels = {
            "date_intervention": "Date d'intervention",
            "description": "Description du problème ou de la maintenance",
            "technicien": "Technicien",
            "statut": "Statut",
        }
        widgets = {
            "date_intervention": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Expliquez pourquoi l'appareil nécessite une maintenance."}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ne proposer que les techniciens actifs dans la liste déroulante,
        # sauf s'il s'agit d'une intervention existante déjà liée à un
        # technicien devenu inactif entre-temps (on ne veut pas le faire
        # disparaître silencieusement du formulaire d'édition).
        queryset = Technicien.objects.filter(actif=True)
        if self.instance and self.instance.technicien_id:
            queryset = queryset | Technicien.objects.filter(pk=self.instance.technicien_id)
        self.fields["technicien"].queryset = queryset.distinct().order_by("nom", "prenom")
        self.fields["technicien"].empty_label = "— Sélectionner un technicien —"


class TechnicienForm(BootstrapModelForm):
    class Meta:
        model = Technicien
        fields = ["nom", "prenom", "email", "telephone", "specialite", "actif"]
        labels = {
            "nom": "Nom",
            "prenom": "Prénom",
            "email": "Email",
            "telephone": "Téléphone",
            "specialite": "Spécialité",
            "actif": "Technicien actif",
        }
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Nom de famille"}),
            "prenom": forms.TextInput(attrs={"placeholder": "Prénom"}),
            "specialite": forms.TextInput(attrs={"placeholder": "Ex. Hardware, Réseau, Logiciel…"}),
        }


class AffectationForm(BootstrapModelForm):
    """Formulaire dédié au changement d'affectation d'un appareil.
    Laisser le champ vide retire l'appareil à son utilisateur actuel."""

    class Meta:
        model = Appareil
        fields = ["utilisateur"]
        labels = {"utilisateur": "Utilisateur"}
        help_texts = {
            "utilisateur": "Laissez vide pour retirer l'appareil à son utilisateur actuel.",
        }
