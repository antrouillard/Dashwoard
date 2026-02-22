# WoW Progress Hub — Contexte du projet

Dashboard personnel pour suivre la progression World of Warcraft : personnages, guilde, crafting, todos, activités hebdomadaires et économie.

---

## Stack technique

| Couche      | Techno                                               |
|-------------|------------------------------------------------------|
| Frontend    | React 18 + Vite, React Router v6, Tailwind CSS       |
| UI          | Composants custom "warcraftcn" (Badge, Button, Skeleton, DropdownMenu) |
| Backend     | FastAPI (Python), SQLAlchemy ORM, Pydantic v2        |
| Base de données | MySQL (via PyMySQL)                              |
| Cache       | Redis (optionnel, configuré mais pas encore utilisé côté frontend) |
| Serveur dev | `uvicorn main:app --reload` sur `localhost:8000`     |
| Frontend dev| `pnpm dev` sur `localhost:5173`                      |

---

## Architecture globale

```
frontend (Vite/React)
  └── src/
       ├── pages/          # Pages React
       ├── components/     # Composants réutilisables
       ├── hooks/          # useQuery / useMutation / hooks WoW
       ├── lib/api.js      # Client HTTP centralisé
       ├── data/           # Données statiques (mockData, activities)
       └── index.css       # Tokens CSS (design system)

backend (FastAPI)
  └── app/
       ├── api/routes/     # Endpoints REST
       ├── models/         # ORM SQLAlchemy
       ├── schemas/        # Pydantic I/O
       ├── services/       # Clients externes (Blizzard, Raider.io, Wowhead)
       ├── core/config.py  # Settings depuis .env
       └── db.py           # Moteur SQLAlchemy + session
```

---

## Configuration (.env)

Variables lues par `backend/app/core/config.py` via `pydantic-settings` :

| Variable                   | Défaut                                      | Description                            |
|----------------------------|---------------------------------------------|----------------------------------------|
| `DATABASE_URL`             | `mysql+pymysql://root:root@localhost:3306/wow_progress` | Connexion MySQL          |
| `REDIS_URL`                | `redis://localhost:6379/0`                  | Cache Redis                            |
| `BLIZZARD_CLIENT_ID`       | —                                           | App Blizzard Developer Portal          |
| `BLIZZARD_CLIENT_SECRET`   | —                                           | Secret OAuth2                          |
| `BLIZZARD_REDIRECT_URI`    | `http://localhost:8000/auth/callback`       | Callback OAuth2                        |
| `BLIZZARD_REGION`          | `eu`                                        | Région API Blizzard                    |
| `BLIZZARD_REALM`           | `archimonde`                                | Serveur par défaut                     |
| `ALLOWED_ORIGINS`          | `["http://localhost:5173","http://localhost:4173"]` | CORS                          |
| `FRONTEND_URL`             | `http://localhost:5173`                     | Redirection après OAuth                |

---

## Base de données — Modèles

### `accounts`
Compte WoW principal. Peut en avoir plusieurs (altruiste, multi-compte).

| Champ                       | Type    | Description                              |
|-----------------------------|---------|------------------------------------------|
| `id`                        | int PK  |                                          |
| `name`                      | str     | Nom de compte (ex : "Harmonie")          |
| `realm`                     | str     | Serveur (ex : "Hyjal")                   |
| `region`                    | str     | "eu" / "us"                              |
| `is_default`                | bool    | Compte affiché par défaut                |
| `blizzard_access_token`     | str     | Token OAuth2 stocké en DB                |
| `blizzard_refresh_token`    | str     | Refresh token                            |
| `blizzard_token_expires_at` | datetime|                                          |
| `blizzard_battletag`        | str     | BattleTag récupéré après connexion       |

### `characters`
Personnages liés à un compte.

| Champ                 | Type    | Description                                 |
|-----------------------|---------|---------------------------------------------|
| `name`, `realm`, `region` | str | Identité Blizzard                        |
| `class_name`, `spec`, `role` | str | Classe / spé / rôle (DPS/Heal/Tank)   |
| `level`, `race`, `faction` | str | Infos générales                         |
| `ilvl`, `ilvl_equipped` | int  | Item level total et équipé                  |
| `mythic_score`        | float   | Score M+ Blizzard                           |
| `gold`                | int     | En copper (1 or = 10 000 copper)            |
| `raiderio_score`      | float   | Score Raider.io                             |
| `raiderio_best_runs`  | JSON str| Meilleures runs stockées en JSON            |
| `account_id`          | FK      | Compte propriétaire                         |
| `guild_id`            | FK?     | Guilde (optionnel)                          |

### `guilds`
Guildes rattachées au dashboard.

| Champ           | Type | Description                          |
|-----------------|------|--------------------------------------|
| `name`, `realm` | str  |                                      |
| `member_count`  | int  |                                      |
| `raid_name`     | str  | Raid du tier courant                 |
| `raid_progress` | JSON | `[{label, done, total}]` sérialisé   |

### `todos`
Tâches libres par personnage.

| Champ          | Type | Description                             |
|----------------|------|-----------------------------------------|
| `title`        | str  | Intitulé de la tâche                    |
| `description`  | str? | Détail optionnel                        |
| `status`       | enum | `a_faire` → `en_cours` → `termine`     |
| `character_id` | FK   |                                         |

### `professions`
Métiers d'un personnage (recréés à chaque sync Blizzard).

| Champ         | Type | Description                  |
|---------------|------|------------------------------|
| `name`        | str  | Nom FR ou EN                 |
| `kp_current`  | int  | Points de connaissance       |
| `kp_max`      | int  | Cap                          |
| `character_id`| FK   |                              |

### `weekly_activities`
Activités hebdomadaires rattachées à un personnage et une semaine de reset.

| Champ             | Type | Description                             |
|-------------------|------|-----------------------------------------|
| `activity_type`   | str  | Ex : "vault_m+", "world_boss"           |
| `detail`          | str? | Infos complémentaires                   |
| `status`          | enum | `a_faire` → `en_cours` → `termine`     |
| `week_start_date` | date | Mardi du reset EU (calculé auto)        |
| `character_id`    | FK   |                                         |

### `crafting_orders`
Commandes de craft à traiter par profession.

| Champ        | Type | Description                      |
|--------------|------|----------------------------------|
| `client`     | str  | Nom du demandeur                 |
| `item_name`  | str  | Nom de l'objet à crafter         |
| `item_id`    | int? | ID Wowhead (résolu auto)         |
| `recipe_id`  | int? | ID recette Blizzard              |
| `profession` | str  |                                  |
| `status`     | enum | `a_faire` → `en_cours` → `termine` |
| `profit_gold`| int  | Bénéfice estimé en gold          |
| `character_id`| FK  |                                  |

### `crafting_goals`
Objectifs de craft à long terme (ex : arme mythique, potion en volume).

| Champ          | Type | Description                         |
|----------------|------|-------------------------------------|
| `title`, `detail` | str |                                   |
| `progress_pct` | int  | 0–100                               |
| `profession`   | str  |                                     |
| `item_id`, `recipe_id` | int? | IDs résolus                 |
| `character_id` | FK   |                                     |
| `reagent_quantities` | rel | Quantités possédées par réactif |

### `crafting_goal_reagents`
Quantités possédées pour chaque réactif d'un objectif (`goal_id + item_id` unique).

### `crafting_recipe_cache`
Cache DB des détails de recette (réactifs) pour éviter de re-scraper Wowhead à chaque démarrage.

### `ah_prices`
Prix minimum AH (commodités EU-wide) par `item_id`. Mis à jour en bloc via `/crafting/ah-prices/sync`.

### `profitability_results`
Cache des résultats d'analyse de rentabilité par profession et recette.

---

## API Backend — Endpoints

Base URL : `http://localhost:8000`

### Health
| Méthode | Route     | Description       |
|---------|-----------|-------------------|
| GET     | `/health` | Status + version  |

### Comptes — `/api/accounts`
| Méthode | Route                   | Description                         |
|---------|-------------------------|-------------------------------------|
| GET     | `/api/accounts`         | Liste tous les comptes               |
| GET     | `/api/accounts/default` | Compte par défaut (ou premier)       |
| GET     | `/api/accounts/{id}`    | Un compte                            |
| POST    | `/api/accounts`         | Créer un compte                      |
| PATCH   | `/api/accounts/{id}`    | Modifier (dont `is_default`)         |
| DELETE  | `/api/accounts/{id}`    | Supprimer                            |

### Personnages — `/api/characters`
| Méthode | Route                      | Description                              |
|---------|----------------------------|------------------------------------------|
| GET     | `/api/characters`          | Liste (filtre `?account_id=`)            |
| GET     | `/api/characters/{id}`     | Un personnage (avec todos + professions) |
| POST    | `/api/characters`          | Créer                                    |
| PATCH   | `/api/characters/{id}`     | Modifier                                 |
| DELETE  | `/api/characters/{id}`     | Supprimer                                |

### Todos — `/api/todos`
| Méthode | Route                       | Description                             |
|---------|-----------------------------|-----------------------------------------|
| GET     | `/api/todos`                | Tous (filtre `?character_id=`)          |
| POST    | `/api/todos`                | Créer                                   |
| PATCH   | `/api/todos/{id}`           | Modifier (titre, description, statut)   |
| PATCH   | `/api/todos/{id}/advance`   | Cycle statut : a_faire→en_cours→termine |
| DELETE  | `/api/todos/{id}`           | Supprimer                               |

### Guildes — `/api/guilds`
| Méthode | Route                | Description |
|---------|----------------------|-------------|
| GET     | `/api/guilds`        | Liste        |
| GET     | `/api/guilds/{id}`   | Une guilde   |
| POST    | `/api/guilds`        | Créer        |
| PATCH   | `/api/guilds/{id}`   | Modifier     |
| DELETE  | `/api/guilds/{id}`   | Supprimer    |

### Auth OAuth2 Blizzard — `/auth`
Monté **sans** préfixe `/api` car l'URL de callback Blizzard est fixe.

| Méthode | Route                       | Description                                        |
|---------|-----------------------------|----------------------------------------------------|
| GET     | `/auth/login?account_id=`   | Redirige vers la page de login Blizzard            |
| GET     | `/auth/callback`            | Reçoit le code OAuth, stocke le token, redirige vers le frontend avec `?sync_success=1&account_id=X` |
| GET     | `/auth/status/{account_id}` | Indique si le token est valide (`is_connected`)    |

### Synchronisation Blizzard — `/api/sync`
Requiert un token valide stocké pour le compte.

| Méthode | Route                                  | Description                                      |
|---------|----------------------------------------|--------------------------------------------------|
| POST    | `/api/sync/account/{account_id}`       | Sync tous les personnages du compte              |
| POST    | `/api/sync/character/{character_id}`   | Sync un seul personnage                          |
| POST    | `/api/sync/raiderio/account/{id}`      | Sync Raider.io de tous les persos du compte      |
| POST    | `/api/sync/raiderio/character/{id}`    | Sync Raider.io d'un personnage                   |

La sync Blizzard récupère : profil, équipement, score M+, professions.

### Activités hebdomadaires — `/api/weekly`
Le reset EU est le **mardi à 09h00 UTC**. Le backend calcule automatiquement `week_start_date`.

| Méthode | Route                         | Description                                  |
|---------|-------------------------------|----------------------------------------------|
| GET     | `/api/weekly`                 | Activités de la semaine courante (filtre `?character_id=`, `?week=YYYY-MM-DD` ou `all`) |
| GET     | `/api/weekly/info`            | Date de reset courant + prochain reset       |
| POST    | `/api/weekly`                 | Créer une activité                           |
| PATCH   | `/api/weekly/{id}`            | Modifier                                     |
| PATCH   | `/api/weekly/{id}/advance`    | Cycle statut                                 |
| DELETE  | `/api/weekly/{id}`            | Supprimer                                    |

### Crafting — `/api/crafting`
Système complet de gestion craft : commandes, objectifs, recettes, prix AH, rentabilité.

**Commandes**

| Méthode | Route                               | Description                         |
|---------|-------------------------------------|-------------------------------------|
| GET     | `/api/crafting/orders`              | Liste (filtres : character_id, profession, status) |
| GET     | `/api/crafting/orders/{id}`         |                                     |
| POST    | `/api/crafting/orders`              | Crée (résout item_id depuis recipe_id auto) |
| PATCH   | `/api/crafting/orders/{id}`         | Modifier                            |
| PATCH   | `/api/crafting/orders/{id}/advance` | Cycle statut                        |
| DELETE  | `/api/crafting/orders/{id}`         |                                     |

**Objectifs**

| Méthode | Route                                          | Description                    |
|---------|------------------------------------------------|--------------------------------|
| GET     | `/api/crafting/goals`                          | Liste (filtres : character_id, profession) |
| GET/POST/PATCH/DELETE | `/api/crafting/goals/{id}`        | CRUD                           |
| GET     | `/api/crafting/goals/reagents`                 | Toutes les quantités possédées |
| PATCH   | `/api/crafting/goals/{id}/reagents/{item_id}`  | Modifier qty possédée          |

**Recettes & Blizzard static**

| Méthode | Route                                            | Description                        |
|---------|--------------------------------------------------|------------------------------------|
| GET     | `/api/crafting/professions/{name}/recipes`       | Recettes d'une profession (via API Blizzard) |
| GET     | `/api/crafting/recipes/{recipe_id}`              | Détail d'une recette (réactifs)    |
| GET     | `/api/crafting/recipes/cache`                    | Charge tout le cache recette DB    |
| GET     | `/api/crafting/search-item?q=`                   | Recherche item Wowhead             |

**Prix AH & rentabilité**

| Méthode | Route                                      | Description                          |
|---------|--------------------------------------------|--------------------------------------|
| GET     | `/api/crafting/ah-prices/status`           | Date de la dernière sync AH          |
| GET     | `/api/crafting/ah-prices/items?ids=`       | Prix de plusieurs items              |
| POST    | `/api/crafting/ah-prices/sync`             | Resync prix commodités Blizzard AH   |
| GET     | `/api/crafting/profitability?profession=`  | Rentabilité calculée (cache)         |
| POST    | `/api/crafting/profitability/analyze`      | Recalcule la rentabilité             |

---

## Services externes

### `services/blizzard.py`
- **OAuth2** : `build_auth_url`, `exchange_code_for_token`, token applicatif (client credentials) avec cache mémoire 24h.
- **Profil personnage** : `get_character_profile`, `get_character_equipment`, `get_mythic_profile`, `get_professions`.
- **Parsing** : `parse_character_update`, `parse_mythic_score`, `parse_professions`.
- **Recettes** : `get_recipes_for_profession`, `get_recipe_detail`, `get_item_media` — avec cache mémoire 24h et filtrage des pseudo-recettes (titres de section Blizzard).
- **AH Commodités** : `get_commodity_prices` — récupère les prix de toutes les commodités EU en une seule requête.
- Mapping `PROFESSION_IDS` FR+EN → ID Blizzard.

### `services/raiderio.py`
- API publique (pas de token requis).
- `get_character_profile` → score M+, classements monde/région/realm, meilleures runs.
- `parse_raiderio` : extrait les champs utiles vers les colonnes `Character`.

### `services/wowhead.py`
- Scraping Wowhead (fallback quand l'API Blizzard static est indisponible).
- `search_item(name)` → `{item_id, item_name}`.
- `get_reagents(item_id)` → liste des réactifs avec quantités.

---

## Frontend — Pages et fonctionnalités

### Navigation (App.jsx)
Barre de navigation permanente avec : **Dashboard · Personnages · Guilde · Crafting · Economie · Todos · Activites**

Bouton **Compte** (dropdown) + bouton **Connecter Blizzard / Sync Blizzard**.  
Après le callback OAuth (`?sync_success=1&account_id=X`), la sync se déclenche automatiquement.

---

### Dashboard (`/`)
Vue d'ensemble consolidée.

**Panel Activités** (colonne gauche, 3/12)
- Affiche la **semaine courante** d'après le calendrier `activities.js`.
- Mini barre de progression (tâches cochées / total).
- Bannière amber si une restriction Crests est active.
- Jusqu'à 5 tâches "Priorité" de la semaine avec checkboxes.
- État partagé avec la page Activités via `localStorage`.
- Lien "Tout voir →" vers `/activites`.

**Panel Personnages** (5/12)
- Liste les personnages du compte par défaut.
- Affiche : nom, classe/rôle/spec, score M+, or (converti depuis copper), métiers, ilvl.
- Skeleton pendant le chargement.

**Panel Vue d'ensemble + Guilde** (4/12)
- Statistiques globales (persos actifs, or total, M+ moyen) depuis `mockData`.
- Progression de guilde (raid, boss suivant, trackers Normal/Héroïque/Mythique).

**Panel Prix AH** (6/12) — données mock pour l'instant.

**Panel Todos** (6/12)
- Liste tous les todos de tous les personnages.
- Clic sur le badge de statut → avance le cycle.
- Barre de progression globale (animation rainbow à 100%).

---

### Personnages (`/personnages`)
CRUD personnages du compte sélectionné.
- Formulaire d'ajout (nom, realm, classe, spec, rôle, guild_id).
- Suppression avec confirmation.
- Boutons sync Blizzard et Raider.io par personnage.
- Affichage détaillé : ilvl, rôle, spec, or, professions, score M+.

---

### Crafting (`/crafting`)
Gestion complète du crafting.

**Onglets :** Commandes · Objectifs · Recettes · Rentabilité

**Commandes** : tableau des commandes à crafter (client, item, profession, statut, bénéfice). Avancement de statut en un clic.

**Objectifs** : objectifs de production à long terme avec barre de progression, détail des réactifs et quantités possédées (persistées en DB). L'`ItemSelector` permet de chercher une recette par profession et d'auto-remplir les réactifs depuis Blizzard/Wowhead.

**Recettes** : navigation par profession, liste des recettes disponibles chargées depuis l'API Blizzard avec cache DB.

**Rentabilité** : calcul de marge craft vs prix AH. Déclenche `POST /crafting/profitability/analyze`.

---

### Todos (`/todos`)
Gestionnaire de tâches par personnage.

- Filtres par statut (`tous / à faire / en cours / terminé`) et par personnage.
- Formulaire de création rapide avec preset d'activités WoW courantes (Vault M+, World Boss, Catalyseur, etc.).
- Champ de recherche par titre.
- Clic sur badge → avance le cycle de statut.
- Suppression avec double-confirmation.
- Panel "Activités hebdo" en sidebar : affiche les `weekly_activities` de la semaine (depuis l'API `/api/weekly`).

---

### Activités (`/activites`)
Programme de progression saison TWW Season 1 2026 — **entièrement frontend, sans API**.

**Calendrier des semaines** (9 semaines, Early Access → Week 9+) :

| ID           | Titre       | Dates            |
|--------------|-------------|------------------|
| early-access | Early Access| 26 fév – 2 mars  |
| preseason-w1 | Week 1      | 3 – 9 mars       |
| preseason-w2 | Week 2      | 10 – 16 mars     |
| s1-w1        | Week 3      | 17 – 23 mars     |
| s1-w2        | Week 4      | 24 – 30 mars     |
| s1-w3        | Week 5      | 31 mars – 6 avr  |
| s1-w4        | Week 6      | 7 – 13 avr       |
| s1-w5        | Week 7      | 14 – 20 avr      |
| s1-w6        | Week 8      | 21 – 27 avr      |
| s1-w7        | Week 9+     | 28 avr+          |

- **Sélecteur de semaine** : met en surbrillance la semaine courante (calculée automatiquement par `getCurrentWeek()`).
- **Checklist** : chaque tâche est cochable, avec distinction visuelle "Priorité".
- **Bannière amber** si restriction Crests active pour la semaine.
- **Barre de progression** par semaine.
- **Panel Suivi Crests** et **Item Level cible** (affiché quand disponibles).
- **Planning overview** : sidebar récapitulant toutes les semaines avec leur avancement.
- État persisté dans `localStorage` sous la clé `wow-activities-done` — partagé avec le panel Dashboard.

---

### Guilde (`/guilde`) et Économie (`/economie`)
Pages placeholder — marquées "En préparation".

---

## Hooks frontend

### `useApi.js`
Deux hooks génériques :
- **`useQuery(fetcher, deps)`** : charge des données GET, gère `loading`, `error`, `refetch`. Re-fetch quand `deps` changent.
- **`useMutation(mutationFn)`** : POST/PATCH/DELETE, gère `loading`/`error`, retourne `mutate`.

### `useWow.js`
Hooks métier construits sur `useQuery`/`useMutation` :

| Hook                     | Description                                |
|--------------------------|--------------------------------------------|
| `useDefaultAccount()`    | Compte par défaut                          |
| `useAccounts()`          | Tous les comptes                           |
| `useCharacters(accountId)` | Personnages d'un compte                  |
| `useCreateCharacter(cb)` | Créer un personnage                        |
| `useDeleteCharacter(cb)` | Supprimer un personnage                    |
| `useTodos(characterId)`  | Todos d'un personnage                      |
| `useAllTodos()`          | Tous les todos                             |
| `useAdvanceTodo(cb)`     | Avancer le statut d'un todo                |
| `useCreateTodo(cb)`      | Créer un todo                              |
| `useDeleteTodo(cb)`      | Supprimer un todo                          |
| `useGuilds()`            | Toutes les guildes                         |
| `useAuthStatus(accountId)` | Statut connexion Blizzard              |
| `useBlizzardLogin()`     | Déclenche le flow OAuth (redirection)      |
| `useSyncAccount(cb)`     | Sync Blizzard d'un compte complet          |
| `useWeekly(characterId)` | Activités hebdo d'un personnage            |

---

## Client API (`src/lib/api.js`)

Client HTTP centralisé. Base URL : `VITE_API_URL` ou `http://localhost:8000/api`.

Couvre tous les domaines : `accounts`, `characters`, `todos`, `guilds`, `sync`, `weekly`, `crafting` (orders, goals, recipes, profitability, ah-prices, admin).

---

## Design system

Fichier `src/index.css` + `src/components/ui/warcraftcn/`.

- Thème sombre "fantasy" : fond `hsl(220 30% 8%)`, accent gold `hsl(42 70% 55%)`, typo `Cinzel` (titres) + `IBM Plex Sans` (corps).
- Classes utilitaires : `.dashboard-shell`, `.dashboard-grid`, `.panel-frame`, `.panel-header`, `.panel-body`, `.panel-title`, `.panel-subtitle`, `.dense-table`, `.stat-pill`, `.rainbow-progress`.
- Composants UI : `Badge` (variantes default/secondary/outline), `Button` (variante frame), `Skeleton`, `DropdownMenu`.

---

## Données mock (`src/data/mockData.js`)

Utilisées en fallback pour les sections pas encore connectées à l'API :
- `account` : nom/realm de démonstration.
- `heroStats` : persos actifs, or total, M+ moyen.
- `weekly` : activités hebdo demo (remplacées sur Dashboard par le calendrier activities.js).
- `market` : prix AH démo.
- `guild` : progression de guilde démo.
- `craftingGoals`, `professions`, `todos` : exemples.

---

## Lancer le projet

```bash
# Backend
cd backend
uvicorn main:app --reload
# → http://localhost:8000
# → Swagger : http://localhost:8000/docs

# Frontend
pnpm dev
# → http://localhost:5173
```

Docker Compose disponible dans `backend/docker-compose.yml` pour MySQL + Redis.
