from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction

from parc_informatique.models import Appareil, HistoriqueMaintenance, Local, Technicien, Utilisateur
from parc_informatique.roles import TECHNICIEN


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
            'fournisseur',
            'prix_achat',
            'date_fin_garantie',
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
            'fournisseur': 'Fournisseur',
            'prix_achat': "Prix d'achat (€)",
            'date_fin_garantie': 'Fin de garantie',
            'localisation': 'Localisation',
            'utilisateur': 'Utilisateur',
        }
        widgets = {
            "nom": forms.TextInput(attrs={"placeholder": "Ex. PC-Comptabilité-01"}),
            "marque": forms.TextInput(attrs={"placeholder": "Ex. Dell, HP, Lenovo…"}),
            "modele": forms.TextInput(attrs={"placeholder": "Ex. Latitude 5540"}),
            "numero_serie": forms.TextInput(attrs={"placeholder": "Numéro de série constructeur"}),
            "date_acquisition": forms.DateInput(attrs={"type": "date"}),
            "fournisseur": forms.TextInput(attrs={"placeholder": "Ex. Grosbill, CDiscount Pro…"}),
            "prix_achat": forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"}),
            "date_fin_garantie": forms.DateInput(attrs={"type": "date"}),
        }


class ModificationAppareilForm(BootstrapModelForm):
    class Meta:
        model = Appareil
        fields = ['etat']
        labels = {'etat': 'Etat'}


class HistoriqueMaintenanceForm(BootstrapModelForm):
    class Meta:
        model = HistoriqueMaintenance
        fields = ["date_intervention", "description", "technicien", "statut", "cout"]
        labels = {
            "date_intervention": "Date d'intervention",
            "description": "Description du problème ou de la maintenance",
            "technicien": "Technicien",
            "statut": "Statut",
            "cout": "Coût (€, optionnel)",
        }
        widgets = {
            "date_intervention": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(
                attrs={"rows": 4, "placeholder": "Expliquez pourquoi l'appareil nécessite une maintenance."}
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
            queryset = queryset | Technicien.objects.filter(pk=self.instance.technicien_id)
        self.fields["technicien"].queryset = queryset.distinct().order_by("nom", "prenom")
        self.fields["technicien"].empty_label = "— Sélectionner un technicien —"


class TechnicienForm(BootstrapModelForm):
    class Meta:
        model = Technicien
        fields = ["nom", "prenom", "email", "telephone", "specialite", "actif", "compte_utilisateur"]
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
            "specialite": forms.TextInput(attrs={"placeholder": "Ex. Hardware, Réseau, Logiciel…"}),
        }

    # --- Création optionnelle d'un compte de connexion (champs hors modèle) ---
    creer_compte = forms.BooleanField(
        required=False,
        label="Créer un compte de connexion pour ce technicien",
        help_text=(
            "Le compte recevra uniquement le rôle Technicien. "
            "Pour relier un compte déjà existant, utilisez plutôt la liste ci-dessus."
        ),
    )
    identifiant = forms.CharField(
        required=False,
        max_length=150,
        label="Identifiant de connexion",
        widget=forms.TextInput(attrs={"placeholder": "Ex. m.durand", "autocomplete": "off"}),
    )
    mot_de_passe = forms.CharField(
        required=False,
        label="Mot de passe initial",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=(
            "À communiquer au technicien, qui pourra ensuite le changer "
            "lui-même dans Paramètres."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compte_cree = None  # renseigné par save() si un compte est créé

        self.fields["compte_utilisateur"].required = False
        self.fields["compte_utilisateur"].empty_label = "— Aucun compte associé —"
        self.fields["compte_utilisateur"].help_text = (
            "Optionnel : permet à ce technicien de voir ses propres "
            "interventions une fois connecté (\"Mes interventions\")."
        )

        if self.instance.pk and self.instance.compte_utilisateur_id:
            # Compte déjà relié : rien à créer, on retire les champs concernés.
            for nom in ("creer_compte", "identifiant", "mot_de_passe"):
                del self.fields[nom]
        else:
            # Le JS (main.js) masque identifiant/mot de passe tant que la case
            # n'est pas cochée ; sans JS, les champs restent simplement visibles.
            self.fields["creer_compte"].widget.attrs["data-pi-toggle-fields"] = (
                "id_identifiant,id_mot_de_passe"
            )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("creer_compte"):
            return cleaned  # case décochée (ou champs retirés) : rien à valider

        User = get_user_model()

        if cleaned.get("compte_utilisateur"):
            self.add_error(
                "creer_compte",
                "Choisissez soit un compte existant, soit la création d'un nouveau compte, pas les deux.",
            )
            return cleaned

        identifiant = (cleaned.get("identifiant") or "").strip()
        mot_de_passe = cleaned.get("mot_de_passe") or ""

        if not identifiant:
            self.add_error("identifiant", "Obligatoire pour créer un compte.")
        else:
            try:
                User.username_validator(identifiant)
            except ValidationError as exc:
                self.add_error("identifiant", exc)
            else:
                # iexact : "Marc" et "marc" seraient deux comptes distincts pour
                # Django, mais source de confusion évidente à la connexion.
                if User.objects.filter(username__iexact=identifiant).exists():
                    self.add_error("identifiant", "Cet identifiant est déjà utilisé.")

        if not mot_de_passe:
            self.add_error("mot_de_passe", "Obligatoire pour créer un compte.")
        else:
            utilisateur_temporaire = User(
                username=identifiant,
                email=cleaned.get("email", ""),
                first_name=cleaned.get("prenom", ""),
                last_name=cleaned.get("nom", ""),
            )
            try:
                # Applique AUTH_PASSWORD_VALIDATORS (longueur, mots de passe
                # courants, similarité avec l'identifiant/nom...).
                validate_password(mot_de_passe, user=utilisateur_temporaire)
            except ValidationError as exc:
                self.add_error("mot_de_passe", exc)

        return cleaned

    def save(self, commit=True):
        if not self.cleaned_data.get("creer_compte"):
            return super().save(commit=commit)

        if not commit:
            raise ValueError("Créer un compte exige commit=True (compte et fiche sont enregistrés ensemble).")

        User = get_user_model()
        # Atomique : si l'enregistrement de la fiche échoue, aucun compte orphelin.
        with transaction.atomic():
            utilisateur = User.objects.create_user(
                username=self.cleaned_data["identifiant"].strip(),
                email=self.cleaned_data.get("email", ""),
                password=self.cleaned_data["mot_de_passe"],
                first_name=self.cleaned_data.get("prenom", ""),
                last_name=self.cleaned_data.get("nom", ""),
            )
            groupe, _ = Group.objects.get_or_create(name=TECHNICIEN)
            utilisateur.groups.add(groupe)

            self.instance.compte_utilisateur = utilisateur
            technicien = super().save(commit=True)

        self.compte_cree = utilisateur
        return technicien


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
            "poste": forms.TextInput(attrs={"placeholder": "Ex. Comptable, Chef de projet…"}),
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
            "nom": forms.TextInput(attrs={"placeholder": "Ex. Salle serveur, Bureau 204…"}),
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
