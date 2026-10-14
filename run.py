"""Entry point for the GURPS-Sheet-Manager web application."""

import argparse
import threading
import webbrowser
from pathlib import Path

from app import create_app
from database.connection import (
    DEFAULT_DATABASE_PATH,
    get_database_path,
    initialize_database,
    set_database_path,
    validate_database,
)
from database.settings import (
    get_stored_database_path,
    push_recent_database,
    store_database_path,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="GURPS-Sheet-Manager - interface de administracao do banco de dados."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument(
        "--database",
        help="Caminho do banco de dados a usar. Se nao existir, um banco vazio e criado.",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Nao abre o navegador automaticamente.",
    )
    return parser.parse_args()


def configure_database(arguments: argparse.Namespace) -> None:
    """Resolves the initial database path: CLI argument, stored preference, default."""
    if arguments.database:
        target = Path(arguments.database).expanduser().resolve()
        if target.exists():
            problems = validate_database(target)
            if problems:
                raise SystemExit(
                    "O banco indicado em --database nao e compativel: "
                    + " ".join(problems)
                )
        else:
            initialize_database(target)
            print(f"Banco de dados criado em {target}")
        set_database_path(target)
        store_database_path(target)
        push_recent_database(target)
        return

    stored = get_stored_database_path()
    if stored is not None:
        if not stored.is_file():
            print(
                f"Aviso: o banco configurado nao foi encontrado ({stored}). "
                "Usando o banco padrao."
            )
        else:
            problems = validate_database(stored)
            if problems:
                print(
                    f"Aviso: o banco configurado e incompativel ({stored}): "
                    + " ".join(problems)
                    + " Usando o banco padrao."
                )
            else:
                set_database_path(stored)
                push_recent_database(stored)
                return

    set_database_path(DEFAULT_DATABASE_PATH)
    push_recent_database(DEFAULT_DATABASE_PATH)


def main() -> None:
    arguments = parse_arguments()
    configure_database(arguments)
    initialize_database()

    application = create_app()
    url = f"http://{arguments.host}:{arguments.port}/"

    if not arguments.no_browser:
        threading.Timer(0.8, webbrowser.open, args=(url,)).start()

    print(f"Banco de dados: {get_database_path()}")
    print(f"GURPS-Sheet-Manager disponivel em {url}")
    print("Pressione Ctrl+C para encerrar.")
    application.run(host=arguments.host, port=arguments.port, debug=False)


if __name__ == "__main__":
    main()
