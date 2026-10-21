"""Endpoints that select, create and remember the active database file."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from flask import Blueprint, jsonify, request

from api.errors import ApiError, ConflictError
from database.connection import (
    DEFAULT_DATABASE_PATH,
    get_database_path,
    initialize_database,
    set_database_path,
    validate_database,
)
from database.settings import (
    get_recent_databases,
    push_recent_database,
    remove_recent_database,
    store_database_path,
)

database_blueprint = Blueprint("database", __name__, url_prefix="/api/database")

LOCAL_ADDRESSES = {"127.0.0.1", "::1", "localhost", None}
BROWSE_TIMEOUT_SECONDS = 600

BROWSE_SCRIPT = r"""
import json
import sys
import tkinter as tk
from tkinter import filedialog

mode = sys.argv[1]

try:
    root = tk.Tk()
except tk.TclError as error:
    print(json.dumps({"error": f"Nao foi possivel abrir o dialogo grafico: {error}"}))
    sys.exit(0)

root.withdraw()
root.attributes("-topmost", True)

options = {
    "title": "Selecione o banco de dados",
    "filetypes": [("Bancos SQLite", "*.db"), ("Todos os arquivos", "*.*")],
    "defaultextension": ".db",
}

if mode == "save":
    options["title"] = "Escolha onde criar o novo banco de dados"
    path = filedialog.asksaveasfilename(**options)
else:
    path = filedialog.askopenfilename(**options)

root.destroy()
print(json.dumps({"path": path or ""}))
"""


def _require_local_request() -> None:
    """Blocks database management over non local connections."""
    if request.remote_addr not in LOCAL_ADDRESSES:
        raise ApiError(
            "A gestão de bancos de dados é permitida apenas em conexões locais.",
            403,
        )


def _resolve_path(raw) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ApiError("Informe o caminho do arquivo do banco de dados.")
    return Path(raw.strip()).expanduser().resolve()


def _state_payload() -> dict:
    active = get_database_path()
    return {
        "path": str(active),
        "exists": active.is_file(),
        "is_default": active.resolve() == DEFAULT_DATABASE_PATH.resolve(),
        "default_path": str(DEFAULT_DATABASE_PATH.resolve()),
        "recent": [
            {"path": item, "exists": Path(item).is_file()}
            for item in get_recent_databases()
        ],
    }


def _activate(target: Path) -> dict:
    set_database_path(target)
    store_database_path(target)
    push_recent_database(target)
    return _state_payload()


@database_blueprint.get("")
def database_view():
    return jsonify(_state_payload())


@database_blueprint.post("/select")
def select_database_view():
    _require_local_request()
    payload = request.get_json(silent=True) or {}
    target = _resolve_path(payload.get("path"))

    problems = validate_database(target)
    if problems:
        raise ApiError("Banco de dados incompatível: " + " ".join(problems))

    return jsonify(_activate(target))


@database_blueprint.post("/create")
def create_database_view():
    _require_local_request()
    payload = request.get_json(silent=True) or {}
    target = _resolve_path(payload.get("path"))

    if target.exists():
        raise ConflictError("Já existe um arquivo neste caminho.")

    if not target.parent.is_dir():
        raise ApiError(f"A pasta de destino não existe: {target.parent}")

    try:
        initialize_database(target)
    except (OSError, sqlite3.Error) as error:
        raise ApiError(f"Não foi possível criar o banco de dados: {error}")

    return jsonify(_activate(target)), 201


@database_blueprint.post("/reset")
def reset_database_view():
    _require_local_request()
    initialize_database(DEFAULT_DATABASE_PATH)
    problems = validate_database(DEFAULT_DATABASE_PATH)
    if problems:
        raise ApiError(
            "O banco padrão é incompatível com o esquema atual: " + " ".join(problems)
        )
    return jsonify(_activate(DEFAULT_DATABASE_PATH))


@database_blueprint.post("/browse")
def browse_database_view():
    _require_local_request()
    payload = request.get_json(silent=True) or {}
    mode = payload.get("mode", "open")
    if mode not in {"open", "save"}:
        raise ApiError("Modo de seleção inválido.")

    try:
        result = subprocess.run(
            [sys.executable, "-c", BROWSE_SCRIPT, mode],
            capture_output=True,
            text=True,
            timeout=BROWSE_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise ApiError("O seletor de arquivos ficou aberto por muito tempo. Digite o caminho manualmente.")
    except (OSError, subprocess.SubprocessError):
        raise ApiError(
            "O seletor de arquivos não está disponível neste sistema. "
            "Digite o caminho do banco manualmente."
        )

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or not lines:
        raise ApiError(
            "O seletor de arquivos não está disponível neste sistema. "
            "Digite o caminho do banco manualmente."
        )

    try:
        data = json.loads(lines[-1])
    except ValueError:
        raise ApiError("Resposta inválida do seletor de arquivos.")

    if data.get("error"):
        raise ApiError(
            f"{data['error']} Digite o caminho do banco manualmente."
        )

    selected = data.get("path") or ""
    return jsonify({"path": selected, "cancelled": not selected})


@database_blueprint.delete("/recent")
def remove_recent_database_view():
    _require_local_request()
    target = _resolve_path(request.args.get("path"))
    remove_recent_database(target)
    return ("", 204)
