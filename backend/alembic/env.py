import os
import sys
from logging.config import fileConfig

from alembic import context

# Ajoute backend/ au sys.path pour que "from app..." fonctionne dans cet env.py
# (alembic est lancé depuis backend/ mais n'est pas forcément dans le path).
_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# Charge le .env avant d'importer settings (ALLOWED_ORIGINS requis au boot).
from app.core.config import Settings, load_dotenv

load_dotenv(os.path.join(_HERE, ".env"))
_settings = Settings()

# Importe TOUS les modèles pour que Base.metadata les connaisse.
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tables gérées hors ORM (tables virtuelles sqlite-vec, tables SQLite internes).
# Alembic ne doit ni les créer ni les supprimer.
_ORM_TABLES = {t.name for t in target_metadata.tables.values()}


def _include_object(obj, name, type_, reflected, compare_to):
    """Exclut du diff autogenerate les tables inconnues de l'ORM (ex: vec0)."""
    if type_ == "table" and name not in _ORM_TABLES:
        return False
    return True


def _get_url() -> str:
    """URL dynamique depuis DATABASE_PATH (même logique que session.py)."""
    db_path = _settings.DB_PATH
    return f"sqlite:///{db_path}"


def run_migrations_offline() -> None:
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
        include_object=_include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Réutilise l'engine applicatif : il a déjà l'écouteur "connect" qui charge
    # sqlite-vec (nécessaire pour les tables vec0 du RAG).
    from app.database.session import engine as app_engine

    with app_engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
            include_object=_include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
