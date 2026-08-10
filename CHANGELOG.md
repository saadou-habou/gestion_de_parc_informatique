# Changelog

## [Unreleased]

### ✨ Nouvelles fonctionnalités

#### Authentification & sécurité
- Ajout de l'authentification Django (login/logout, mot de passe oublié, changement de mot de passe) derrière un middleware unique.
- Gestion des rôles Admin/Gestionnaire/Technicien via les Groups Django.
- Centralisation de la logique des rôles dans `roles.py`, partagée entre le site et l'API.
- Ajout d'un journal d'audit (`JournalAudit`) pour les actions sensibles.

#### API JWT
- Ajout d'une API REST `/api/v1/` avec Django REST Framework et SimpleJWT.
- Endpoints pour les appareils, locaux, utilisateurs, techniciens, maintenances et affectations.
- Permissions basées sur les mêmes rôles que le site.
- Documentation interactive avec drf-spectacular / Swagger.

#### Notifications
- Ajout des notifications métier : maintenance en retard, appareil obsolète, garantie bientôt expirée.
- Notifications idempotentes.
- Ajout d'une cloche dans la navbar avec compteur et marquage comme lu.

#### Gestion du parc
- CRUD complet des utilisateurs et locaux.
- Ajout du modèle Technicien avec lien optionnel vers un compte de connexion.
- Ajout de l'historique des affectations.
- Ajout des informations fournisseur, prix d'achat et garantie sur les appareils.
- Ajout du coût et de la date de réparation aux historiques de maintenance.
- Import/export CSV.
- Génération de QR codes pour les appareils.
- Ajout d'une page de statistiques.
- Recherche globale.

#### Frontend
- Intégration de SweetAlert2 pour les confirmations et notifications.

### 🐛 Correctifs
- Correction de la synchronisation entre l'état d'un appareil et ses maintenances.
- Correction de la boucle de redirection dans `LoginRequiredMiddleware`.
- Correction de classes Bootstrap manquantes.
- Enregistrement des modèles manquants dans `admin.py`.

### 🧪 Tests & CI
- Ajout de tests pour les transitions d'état, notifications, permissions, isolation des interventions et import CSV.
- Migration de `requirements.txt` vers `uv` (`pyproject.toml` + `uv.lock`).
- Ajout d'un workflow GitHub Actions pour le lint, les checks, les migrations et les tests.