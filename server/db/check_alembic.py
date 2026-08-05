#!/usr/bin/env python3
"""
Script de vérification de la configuration Alembic
"""

import os
import sys
from pathlib import Path


def check_environment():
    """Vérifier les variables d'environnement"""
    print("🔍 Vérification de l'environnement...")

    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Masquer le mot de passe pour l'affichage
        safe_url = database_url
        if "@" in safe_url:
            parts = safe_url.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split("//")[-1]
                user = user_pass.split(":")[0]
                safe_url = safe_url.replace(user_pass, f"{user}:****")
        print(f"  ✅ DATABASE_URL est définie: {safe_url}")
        return True
    else:
        print(f"  ❌ DATABASE_URL n'est pas définie")
        print(
            f"  💡 Définissez-la avec: export DATABASE_URL='mysql+pymysql://user:password@host:port/database'"
        )
        return False


def check_alembic_files():
    """Vérifier que les fichiers Alembic sont présents"""
    print("\n🔍 Vérification des fichiers Alembic...")

    required_files = [
        "alembic.ini",
        "alembic/env.py",
        "alembic/script.py.mako",
        "alembic/versions",
    ]

    all_present = True
    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            file_type = "📁" if path.is_dir() else "📄"
            print(f"  ✅ {file_type} {file_path}")
        else:
            print(f"  ❌ {file_path} - MANQUANT")
            all_present = False

    return all_present


def check_models():
    """Vérifier que les modèles peuvent être importés"""
    print("\n🔍 Vérification des modèles SQLAlchemy...")

    try:
        # ai_server vit dans server/, un niveau au-dessus de ce script (server/db/)
        server_dir = str(Path(__file__).resolve().parent.parent)
        if server_dir not in sys.path:
            sys.path.insert(0, server_dir)
        from ai_server.dao.database import Base

        tables = Base.metadata.tables
        print(f"  ✅ {len(tables)} tables détectées:")
        for table_name in sorted(tables.keys()):
            print(f"     • {table_name}")
        return True
    except ImportError as e:
        print(f"  ❌ Impossible d'importer les modèles: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Erreur lors de l'import des modèles: {e}")
        return False


def check_alembic_command():
    """Vérifier que la commande alembic est disponible"""
    print("\n🔍 Vérification de la commande alembic...")

    import subprocess

    try:
        result = subprocess.run(
            ["alembic", "--version"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"  ✅ Alembic installé: {version}")
            return True
        else:
            print(f"  ❌ Alembic non disponible")
            return False
    except FileNotFoundError:
        print(f"  ❌ Commande 'alembic' non trouvée")
        print(f"  💡 Installez avec: pip install alembic")
        return False
    except subprocess.TimeoutExpired:
        print(f"  ❌ Timeout lors de l'exécution d'alembic")
        return False


def check_migrations():
    """Vérifier les migrations existantes"""
    print("\n🔍 Vérification des migrations...")

    versions_dir = Path("alembic/versions")
    if not versions_dir.exists():
        print(f"  ⚠️  Répertoire versions/ n'existe pas")
        return False

    migrations = list(versions_dir.glob("*.py"))
    migrations = [m for m in migrations if m.name != "__pycache__"]

    if migrations:
        print(f"  ✅ {len(migrations)} migration(s) trouvée(s):")
        for migration in sorted(migrations):
            print(f"     • {migration.name}")
    else:
        print(f"  ℹ️  Aucune migration trouvée (c'est normal si vous démarrez)")
        print(
            f'  💡 Créez votre première migration avec: make db-create MSG="Initial migration"'
        )

    return True


def main():
    """Fonction principale"""
    print("=" * 60)
    print("  Vérification de la configuration Alembic pour AI Server")
    print("=" * 60)

    # Changer vers le répertoire du script
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    checks = [
        check_environment,
        check_alembic_files,
        check_alembic_command,
        check_models,
        check_migrations,
    ]

    results = [check() for check in checks]

    print("\n" + "=" * 60)
    if all(results[:4]):  # Les 4 premiers checks sont critiques
        print("✅ Configuration Alembic OK!")
        print("\n📚 Prochaines étapes:")
        print("  1. Consultez README.md (dans ce dossier) pour démarrer")
        print("  2. Utilisez `make db-*` pour gérer vos migrations")
    else:
        print("❌ Des problèmes ont été détectés")
        print("\n💡 Consultez README.md (dans ce dossier) pour résoudre les problèmes")
        sys.exit(1)
    print("=" * 60)


if __name__ == "__main__":
    main()
