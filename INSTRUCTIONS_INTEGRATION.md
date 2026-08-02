# Instructions d'intégration

Aucun modèle et aucune règle métier existante n'a été modifié. Deux fichiers
Python sont fournis **complets** (`views.py` et `urls.py`) : il suffit de
remplacer vos fichiers actuels par ceux-ci (ils contiennent 100% de la logique
d'origine + les ajouts ci-dessous).

## Nouveautés ajoutées

1. **Tableau de bord** (`dashboard()`) — stats, alertes, activité récente.
   Route : `/dashboard/`.
2. **Pagination serveur** sur la liste des appareils (`index()`) — 10 par page,
   via `django.core.paginator.Paginator`. La variable de contexte `appareils`
   reste un itérable, donc le template existant (`{% for appareil in appareils %}`)
   continue de fonctionner sans changement de nom.
3. **Gestion des utilisateurs / affectations** :
   - `liste_utilisateurs()` → `/utilisateurs/` — liste paginée + recherche instantanée.
   - `profil_utilisateur()` → `/utilisateurs/<id>/` — coordonnées + appareils
     actuellement affectés.

   ⚠️ **Limite du modèle de données actuel** : `Appareil.utilisateur` est une
   simple clé étrangère vers l'affectation *en cours*. Il n'existe pas de
   modèle d'historique des affectations (pas d'`AffectationHistorique` avec
   dates de début/fin). La page de profil affiche donc les appareils
   affectés **actuellement**, avec une note explicite pour l'utilisateur.
   Si vous voulez un véritable historique des affectations (qui a eu quel
   appareil, et quand), il faudra ajouter un nouveau modèle — dites-le moi
   et je le fais, mais cela sort du "ne pas changer les modèles sauf
   nécessité absolue" que vous aviez posé comme contrainte.

## Fichiers à copier dans votre projet

```
parc_informatique/views.py                                  (remplace l'existant)
parc_informatique/urls.py                                   (remplace l'existant)

templates/parc_informatique/base.html
templates/parc_informatique/dashboard.html
templates/parc_informatique/index.html
templates/parc_informatique/afficher_appareil.html
templates/parc_informatique/appareil-form.html
templates/parc_informatique/appareil_edit_form.html
templates/parc_informatique/confirmer_suppression.html
templates/parc_informatique/envoyer_en_maintenance.html
templates/parc_informatique/historique_maintenance.html
templates/parc_informatique/utilisateurs_liste.html          (nouveau)
templates/parc_informatique/utilisateur_profil.html          (nouveau)
templates/parc_informatique/include/sidebar.html
templates/parc_informatique/include/navbar.html
templates/parc_informatique/include/messages.html
templates/parc_informatique/include/footer.html
templates/parc_informatique/include/pagination.html          (nouveau, composant réutilisable)

static/parc_informatique/css/main.css
static/parc_informatique/js/main.js
```

`404.html` / `500.html` (dans `templates_root/`) vont dans le dossier
`templates/` **à la racine du projet** (celui déclaré dans
`TEMPLATES[0]["DIRS"]` de `settings.py`). Actifs uniquement quand
`DEBUG = False`.

## Routes finales

| URL | Vue | Nom |
|---|---|---|
| `/` | `index` | `parc_informatique:index` (**inchangée**, pour ne rien casser) |
| `/dashboard/` | `dashboard` | `parc_informatique:dashboard` |
| `/appareils/<id>/` | `afficher_appareil` | idem |
| `/ajouter-appareil/` | `ajouter_appareil` | idem |
| `/appareils/<id>/modifier/` | `modifier_appareil` | idem |
| `/appareils/<id>/supprimer/` | `supprimer_appareil` | idem |
| `/appareils/<id>/maintenance/` | `historique_maintenance` | idem |
| `/appareils/<id>/evoyer_en_maintenance/` | `envoyer_en_maintenance` | idem |
| `/utilisateurs/` | `liste_utilisateurs` | **nouveau** |
| `/utilisateurs/<id>/` | `profil_utilisateur` | **nouveau** |

Si vous préférez que `/` pointe directement vers le tableau de bord plutôt
que la liste des appareils, inversez simplement les deux premières lignes de
`urls.py`.

## Anciens fichiers à supprimer

- `include/begin_page.html` et `include/end_page.html` (remplacés par
  `base.html` + `{% extends %}`, ce qui élimine la duplication HTML).

## Autres points corrigés au passage

- `index.html` original affichait `{{ utilisateur.nom }}` sans que cette
  variable existe dans le contexte → supprimé.
- `historique_maintenance.html` original lisait `appareil.maintenances.all`,
  alors que la vue passe `historiquemaintenances` → corrigé.
- La recherche instantanée (JS) filtre uniquement les lignes visibles sur la
  page courante, puisque la pagination est désormais gérée côté serveur ;
  c'est un compromis attendu (résultat cohérent avec la plupart des
  interfaces ITSM/SaaS qui combinent pagination serveur + filtre client par page).
