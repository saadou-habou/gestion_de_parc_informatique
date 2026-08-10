from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from parc_informatique.models import (
    Appareil,
    HistoriqueMaintenance,
    Local,
    Technicien,
    Utilisateur,
)


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
            "nom",
            "type",
            "marque",
            "modele",
            "numero_serie",
            "etat",
            "date_acquisition",
            "fournisseur",
            "prix_achat",
            "date_fin_garantie",
            "localisation",
            "utilisateur",
        ]
        labels = {
            "nom": "Nom",
            "type": "Type",
            "marque": "Marque",
            "modele": "Modèle",
            "numero_serie": "Numéro de série",
            "etat": "Etat",
            "date_acquisition": "Date d'acquisition",
            "fournisseur": "Fournisseur",
            "prix_achat": "Prix d'achat (FCFA)",
            "date_fin_garantie": "Fin de garantie",
            "localisation": "Localisation",
            "utilisateur": "Utilisateur",
        }
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Ex. PC-Comptabilité-01"}),
            "marque": forms.TextInput(attrs={"placeholder": "Ex. Dell, HP, Lenovo…"}),
            "modele": forms.TextInput(attrs={"placeholder": "Ex. Latitude 5540"}),
            "numero_serie": forms.TextInput(
                attrs={"placeholder": "Numéro de série constructeur"}
            ),
            "date_acquisition": forms.DateInput(attrs={"type": "date"}),
            "fournisseur": forms.TextInput(
                attrs={"placeholder": "Ex. Grosbill, CDiscount Pro…"}
            ),
            "prix_achat": forms.NumberInput(
                attrs={"step": "0.01", "placeholder": "0.00"}
            ),
            "date_fin_garantie": forms.DateInput(attrs={"type": "date"}),
        }


class ModificationAppareilForm(BootstrapModelForm):
    class Meta:
        model = Appareil
        fields = ["etat"]
        labels = {"etat": "Etat"}


class HistoriqueMaintenanceForm(BootstrapModelForm):
    class Meta:
        model = HistoriqueMaintenance
        fields = ["date_intervention", "description", "technicien", "statut", "cout"]
        labels = {
            "date_intervention": "Date d'intervention",
            "description": "Description du problème ou de la maintenance",
            "technicien": "Technicien",
            "statut": "Statut",
            "cout": "Coût (FCFA, optionnel)",
        }
        widgets = {
            "date_intervention": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Expliquez pourquoi l'appareil nécessite une maintenance.",
                }
            ),
            "cout": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ne proposer que les techniciens actifs dans la liste déroulante,
        # sauf s'il s'agit d'une intervention existante déjà liée à un
        # technicien devenu inactif entre-temps (on ne veut pas le faire
        # disparaître silencieusement du formulaire d'édition).
        queryset = Technicien.objects.filter(actif=True)
        if self.instance and self.instance.technicien_id:
            queryset = queryset | Technicien.objects.filter(
                pk=self.instance.technicien_id
            )
        self.fields["technicien"].queryset = queryset.distinct().order_by(
            "nom", "prenom"
        )
        self.fields["technicien"].empty_label = "— Sélectionner un technicien —"


class TechnicienForm(BootstrapModelForm):
    class Meta:
        model = Technicien
        fields = [
            "nom",
            "prenom",
            "email",
            "telephone",
            "specialite",
            "actif",
            "compte_utilisateur",
        ]
        labels = {
            "nom": "Nom",
            "prenom": "Prénom",
            "email": "Email",
            "telephone": "Téléphone",
            "specialite": "Spécialité",
            "actif": "Technicien actif",
            "compte_utilisateur": "Compte de connexion associé",
        }
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Nom de famille"}),
            "prenom": forms.TextInput(attrs={"placeholder": "Prénom"}),
            "specialite": forms.TextInput(
                attrs={"placeholder": "Ex. Hardware, Réseau, Logiciel…"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["compte_utilisateur"].required = False
        self.fields["compte_utilisateur"].empty_label = "— Aucun compte associé —"
        self.fields["compte_utilisateur"].help_text = (
            "Optionnel : permet à ce technicien de voir ses propres "
            'interventions une fois connecté ("Mes interventions").'
        )


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


class UtilisateurForm(BootstrapModelForm):
    class Meta:
        model = Utilisateur
        fields = ["nom", "prenom", "email", "telephone", "poste"]
        labels = {
            "nom": "Nom",
            "prenom": "Prénom",
            "email": "Email",
            "telephone": "Téléphone",
            "poste": "Poste",
        }
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Nom de famille"}),
            "prenom": forms.TextInput(attrs={"placeholder": "Prénom"}),
            "poste": forms.TextInput(
                attrs={"placeholder": "Ex. Comptable, Chef de projet…"}
            ),
        }


class LocalForm(BootstrapModelForm):
    class Meta:
        model = Local
        fields = ["nom", "batiment", "etage"]
        labels = {
            "nom": "Nom du local",
            "batiment": "Bâtiment",
            "etage": "Étage",
        }
        widgets = {
            "nom": forms.TextInput(
                attrs={"placeholder": "Ex. Salle serveur, Bureau 204…"}
            ),
            "batiment": forms.TextInput(attrs={"placeholder": "Ex. Bâtiment A"}),
            "etage": forms.TextInput(attrs={"placeholder": "Ex. RDC, 2e étage…"}),
        }


class ImporterAppareilsForm(forms.Form):
    """Import en masse d'appareils depuis un fichier CSV."""

    fichier = forms.FileField(
        label="Fichier CSV",
        help_text=(
            "Colonnes attendues : nom, type, marque, modele, numero_serie, etat, "
            "date_acquisition (AAAA-MM-JJ), fournisseur, prix_achat, date_fin_garantie "
            "(AAAA-MM-JJ), localisation (nom exact d'un local existant), "
            "utilisateur (email exact d'un utilisateur existant). "
            "Seules nom, type et numero_serie sont obligatoires."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fichier"].widget.attrs["class"] = "form-control"
        self.fields["fichier"].widget.attrs["accept"] = ".csv"
