from logging.config import fileConfig
import os
import sys

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Ajouter le répertoire "server" (racine contenant le package ai_server) au
# path pour pouvoir importer les modules. Ce fichier vit à
# server/db/alembic/env.py, donc il faut remonter trois niveaux : alembic -> db -> server.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Importer la configuration et les modèles
from ai_server.config.config import flask_config
from ai_server.dao.database import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Remplacer l'URL de la base de données par celle de la configuration Flask
# Si DATABASE_URL n'est pas définie, utiliser une valeur par défaut ou lever une erreur
if flask_config.DATABASE_URL:
    config.set_main_option('sqlalchemy.url', flask_config.DATABASE_URL)
else:
    # Vérifier si l'URL est déjà définie dans alembic.ini
    if not config.get_main_option('sqlalchemy.url'):
        raise ValueError(
            "DATABASE_URL n'est pas définie. "
            "Définissez la variable d'environnement DATABASE_URL ou "
            "configurez sqlalchemy.url dans alembic.ini"
        )

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# Utiliser les métadonnées de tous vos modèles
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
