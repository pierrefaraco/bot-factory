# Alembic — Guide d'utilisation

Toute la configuration Alembic (config, scripts d'environnement, migrations)
vit dans `server/db/` :

```
server/db/
├── alembic.ini          # Config Alembic (script_location = %(here)s/alembic)
├── alembic/
│   ├── env.py            # Bootstrap : import des modèles ai_server + DATABASE_URL
│   ├── script.py.mako     # Template utilisé pour générer une nouvelle révision
│   └── versions/          # Historique des migrations (une par fichier)
├── check_alembic.py        # Script de diagnostic de la config
├── drop_table.sh / .bat     # Supprime toutes les tables (⚠️ destructif)
└── README.md                # Ce guide
```

> Les commandes de migration (`init` / `create` / `upgrade` / `downgrade` /
> `history` / `current` / `stamp`) sont désormais exposées comme cibles
> `make db-*` à la racine du projet (voir `Makefile`), plus besoin des
> anciens scripts `migrate.sh` / `z-alembic.sh`. Elles s'exécutent via
> `uv run alembic` depuis `server/db/`, avec `DATABASE_URL` chargée
> automatiquement depuis `server/.env`.

## 1. Prérequis (premier lancement)

1. **Environnement virtuel Python installé** (voir `server/CLAUDE.md`) :
   ```bash
   cd server
   uv sync
   ```
2. **Une base MySQL démarrée**, soit via Docker (`make dev` / `make db-only`),
   soit un MySQL local.

## 2. Configurer `DATABASE_URL`

`alembic/env.py` lit la variable d'environnement `DATABASE_URL` (via
`ai_server.config.config.flask_config`). C'est la **même** variable que celle
utilisée par le serveur Flask, définie dans `server/.env` :

```
DATABASE_URL=mysql+pymysql://botcraft_user:123456789@127.0.0.1:3306/botcraft?charset=utf8mb4
```

Les cibles `make db-*` chargent automatiquement `server/.env` avant
d'invoquer `alembic` — inutile de l'exporter manuellement si ce fichier est
à jour.

## 3. Créer le dossier `alembic/` s'il n'existe pas

Le dossier `alembic/` (contenant `env.py`, `script.py.mako`, `versions/`) est
requis par Alembic. S'il venait à manquer (dossier supprimé par erreur,
clone partiel, etc.), régénérez-le avec :

```bash
make db-init
```

Cette commande (voir `server/db/bootstrap_alembic.sh`) ne fait rien si
`alembic/` existe déjà et n'est pas vide (elle ne l'écrase jamais). Si le
dossier est absent, elle exécute `alembic init alembic` **puis** réécrit
automatiquement `alembic/env.py` avec la version personnalisée (import des
modèles `ai_server` + lecture de `DATABASE_URL`) — pas besoin de git pour ça,
tout est autonome dans le script.

> ⚠️ `server/db/` (y compris `alembic/`) n'est pour l'instant pas suivi par
> git dans ce dépôt (`git ls-files server/db` ne retourne rien). Pensez à
> `git add server/db` si vous voulez versionner cette configuration et
> l'historique des migrations.

## 4. Vérifier que tout est en ordre

Un script de diagnostic est fourni :

```bash
cd server && uv run db/check_alembic.py
```

Il vérifie : `DATABASE_URL`, la présence des fichiers Alembic, la commande
`alembic`, l'import des modèles SQLAlchemy (`ai_server.dao.database.Base`) et
les migrations existantes.

## 5. Premier lancement — appliquer les migrations

### Cas A — base de données neuve (aucune table)

Applique toutes les migrations existantes, en partant de zéro :

```bash
make db-upgrade
```

Cela crée toutes les tables définies par la migration initiale
(`d2d0def68081_start.py`) puis toute migration ajoutée depuis.

### Cas B — base de données déjà existante (tables déjà créées manuellement)

Si les tables existent déjà (ex. ancienne base sans suivi Alembic), il ne faut
**pas** rejouer `upgrade` (qui tenterait de recréer les tables). Marquez la
base comme étant déjà à la révision courante sans exécuter le SQL :

```bash
make db-stamp REV=head
```

## 6. Créer une nouvelle migration

Après avoir modifié un modèle dans `server/ai_server/dao/database.py` :

```bash
make db-create MSG="Description du changement"
```

Cela génère un nouveau fichier dans `alembic/versions/` via
`--autogenerate`. **Relisez toujours le fichier généré** (Alembic ne détecte
pas tout parfaitement : renommages de colonnes, changements de type, etc.).

Puis appliquez-la :

```bash
make db-upgrade
```

## 7. Commandes disponibles (`make db-*`)

```bash
make db-init                      # Créer alembic/ s'il n'existe pas (voir section 3)
make db-create MSG="message"      # Nouvelle migration auto-générée
make db-upgrade                   # Appliquer toutes les migrations en attente
make db-downgrade                 # Annuler la dernière migration
make db-history                   # Historique des migrations
make db-current                   # Révision actuelle de la base
make db-stamp REV=<rev|head>      # Marquer la base à une révision sans exécuter le SQL
```

Ce sont des wrappers autour des commandes `alembic` standard ; vous pouvez
aussi utiliser directement `alembic` depuis `server/db/` :

```bash
cd server/db
export DATABASE_URL='mysql+pymysql://botcraft_user:123456789@127.0.0.1:3306/botcraft'
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "message"
```

## 8. Avec Docker Compose

Le `Dockerfile` de l'API copie le dossier `db/` dans l'image (`/app/db`).
Les migrations peuvent aussi se lancer **depuis le conteneur** avec :

```bash
make migrate
# équivalent à :
docker-compose exec -w /app/db api alembic upgrade head
```

> Le `-w /app/db` est nécessaire : Alembic cherche `alembic.ini` dans le
> répertoire courant, et le `WORKDIR` par défaut du conteneur est `/app`.

Pour créer une migration depuis le conteneur :

```bash
docker-compose exec -w /app/db api alembic revision --autogenerate -m "Description"
```

Note : comme le port MySQL du conteneur `db` est publié sur l'hôte
(`3306:3306`), les cibles `make db-*` fonctionnent également contre une base
lancée via `make db-only` / `make dev`, sans avoir besoin de passer par
`docker-compose exec`.

## 9. Réinitialiser complètement la base (destructif)

```bash
cd server/db
./drop_table.sh   # ou drop_table.bat sous Windows natif
```

⚠️ Supprime **toutes** les tables de la base pointée par `DATABASE_URL`. À
utiliser uniquement en développement.

## Notes techniques sur le déplacement vers `server/db/`

Ces fichiers étaient auparavant à la racine de `server/`. Le déplacement vers
`server/db/` a nécessité les correctifs suivants (déjà appliqués) :

- **`alembic.ini`** : `script_location` était un chemin relatif (`alembic`),
  résolu par rapport au **répertoire courant** d'exécution, pas au fichier
  `.ini`. Il pointait donc vers `server/alembic` (inexistant) dès qu'on
  lançait la commande depuis `server/`. Corrigé avec le token `%(here)s` :
  `script_location = %(here)s/alembic`, qui se résout toujours par rapport à
  l'emplacement réel du fichier `alembic.ini`.
- **`alembic/env.py`** : le calcul du `sys.path` pour importer le package
  `ai_server` faisait `dirname(dirname(__file__))`, correct quand le fichier
  était à `server/alembic/env.py` (2 niveaux → `server/`). Maintenant à
  `server/db/alembic/env.py`, il faut remonter un niveau de plus :
  `dirname(dirname(dirname(__file__)))`.
- **`check_alembic.py`** : importait `ai_server.dao.database` en supposant
  être exécuté depuis `server/`. Ajout explicite du dossier parent
  (`server/`) dans `sys.path`.
- **`drop_table.sh` / `drop_table.bat`** : référençaient `tool/drop_tables.py`
  (valide quand le script était dans `server/`, pointant vers
  `server/tool/`). Corrigé en `../tool/drop_tables.py` puisque
  `server/tool/` est maintenant un niveau au-dessus de `server/db/`.
- **Migrations locales** : anciennement gérées par `migrate.sh` /
  `z-alembic.sh` (scripts bash dans `server/db/`), désormais remplacées par
  les cibles `make db-*` à la racine du projet, qui chargent `DATABASE_URL`
  depuis `server/.env` et invoquent `uv run alembic` directement.
- **Docker Compose / Makefile / README / CLAUDE.md** : les commandes
  `docker-compose exec api alembic ...` ne trouvaient plus `alembic.ini`
  (toujours cherché dans le répertoire courant du conteneur, `/app`, alors
  que le fichier est maintenant dans `/app/db`). Corrigé en ajoutant
  `-w /app/db` à `docker-compose exec`.
