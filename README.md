# WoW Progress Hub

Dashboard full-stack pour suivre la progression WoW : personnages, M+, Raider.io, activités hebdo, todos et économie.

**Stack :** React 19 + Vite · FastAPI · MySQL 8.4 · Redis · Docker

---

## Prérequis

- [Node.js 18+](https://nodejs.org/) + [pnpm 10+](https://pnpm.io/)
- [Python 3.12+](https://www.python.org/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

---

## 1. Base de données (Docker)

```bash
cd backend
docker-compose up -d
```

Démarre MySQL 8.4 (port 3306) et Redis 7 (port 6379).  
Les données MySQL sont persistées dans le volume Docker `mysql_data`.

---

## 2. Backend (FastAPI)

### Variables d'environnement

Crée `backend/.env` à partir de l'exemple suivant :

```env
DATABASE_URL=mysql+pymysql://wow_user:wow_password@localhost:3306/wow_progress
REDIS_URL=redis://localhost:6379/0

BLIZZARD_CLIENT_ID=<ton_client_id>
BLIZZARD_CLIENT_SECRET=<ton_client_secret>
BLIZZARD_REDIRECT_URI=http://localhost:8000/auth/callback
BLIZZARD_REGION=eu

ALLOWED_ORIGINS=http://localhost:5173
FRONTEND_URL=http://localhost:5173
```

> Le client Blizzard est à créer sur [develop.battle.net](https://develop.battle.net/).  
> Le redirect URI enregistré doit être exactement `http://localhost:8000/auth/callback`.

### Installation et lancement

```bash
cd backend

# Créer et activer un virtualenv
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Installer les dépendances
pip install -r requirements.txt

# (Optionnel) Seeder la base avec un compte par défaut
python seed.py

# Lancer le serveur (hot-reload)
uvicorn main:app --reload
```

L'API est disponible sur **http://localhost:8000**  
Documentation interactive : **http://localhost:8000/docs**

---

## 3. Frontend (React + Vite)

```bash
# Depuis la racine du projet
pnpm install
pnpm dev
```

Ouvre **http://localhost:5173**

### Build de production

```bash
pnpm build
pnpm preview
```

### Lint

```bash
pnpm lint
```

---

## Pages disponibles

| Route | Description |
|-------|-------------|
| `/` | Dashboard — vue d'ensemble, activités hebdo, todos, personnages |
| `/personnages` | CRUD personnages, sync Blizzard & Raider.io par perso |
| `/todos` | Gestion des tâches avec filtres, ajout rapide, link activités |
| `/crafting` | Suivi des ordres de métier |
| `/guilde` | Progression de guilde *(placeholder)* |
| `/economie` | Prix AH et marché *(placeholder)* |

---

## Fonctionnalités

- **OAuth2 Blizzard** — connexion via Battle.net, sync automatique au retour
- **Sync Blizzard** — ilvl équipé, score M+, or, temps joué, professions
- **Sync Raider.io** — score M+, rangs monde/région/royaume, meilleurs runs
- **Activités hebdo** — reset mardi 09h UTC, cycle de statut à_faire → en_cours → terminé
- **Todos** — ajout depuis activité prédéfinie ou texte libre, lien direct depuis le dashboard
- **Données temps réel** — toutes les pages consomment l'API REST (plus de mock data statique pour les persos/todos)

---

## Structure du projet

```
├── backend/
│   ├── app/
│   │   ├── api/routes/     # accounts, characters, todos, guilds, auth, sync, weekly
│   │   ├── models/         # SQLAlchemy ORM
│   │   ├── schemas/        # Pydantic I/O
│   │   ├── services/       # blizzard.py, raiderio.py
│   │   └── core/config.py  # Paramètres (pydantic-settings)
│   ├── docker-compose.yml
│   ├── main.py
│   ├── seed.py
│   └── requirements.txt
└── src/
    ├── App.jsx             # Layout + navigation + sync Blizzard
    ├── hooks/
    │   ├── useApi.js       # useQuery / useMutation génériques
    │   └── useWow.js       # Hooks métier (comptes, persos, todos, weekly…)
    ├── lib/api.js          # Client HTTP centralisé
    ├── pages/              # DashboardPage, PersonnagesPage, TodosPage, CraftingPage…
    └── components/ui/warcraftcn/   # Composants WarcraftCN
```
