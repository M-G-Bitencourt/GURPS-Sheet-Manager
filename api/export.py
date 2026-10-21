"""PDF export of a complete character sheet using WeasyPrint."""

import unicodedata
from datetime import datetime
from pathlib import Path

from flask import Blueprint, Response, current_app
from weasyprint import HTML

from api.characters import get_character_details
from api.resources import (
    COMBAT_EFFECT_TARGET_LABELS,
    COMBAT_EFFECT_TARGETABLE_TYPES,
    COMBAT_EFFECT_TYPE_LABELS,
    PASSIVE_COMBAT_EFFECT_TYPES,
)

export_blueprint = Blueprint("export", __name__, url_prefix="/api")


def _slugify(value: str, fallback: str) -> str:
    """Builds an ASCII-only token suitable for a download filename."""
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    clean = "".join(
        character if character.isalnum() else "_" for character in ascii_value
    )
    parts = [part for part in clean.split("_") if part]
    return "_".join(parts) or fallback


def build_report_context(character_id: int) -> dict:
    """Aggregates every datum needed by the printable report."""
    details = get_character_details(character_id)
    return {
        "character": details["character"],
        "derived": details["derived"],
        "points": details["points"],
        "skills": details["skills"],
        "spells": details["spells"],
        "advantages": details["advantages"],
        "disadvantages": details["disadvantages"],
        "combat_effects": details["combat_effects"],
        "combat_effect_labels": COMBAT_EFFECT_TYPE_LABELS,
        "combat_effect_target_labels": COMBAT_EFFECT_TARGET_LABELS,
        "combat_effect_targetable_types": COMBAT_EFFECT_TARGETABLE_TYPES,
        "passive_combat_effect_types": PASSIVE_COMBAT_EFFECT_TYPES,
        "additional_stats": details["additional_stats"],
        "inventory": details["inventory"],
        "generated_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }


@export_blueprint.get("/characters/<int:character_id>/export")
def export_character_view(character_id: int):
    report = build_report_context(character_id)
    template = current_app.jinja_env.get_template("character_report.html")
    html_content = template.render(**report)

    static_directory = Path(current_app.root_path) / "static"
    pdf_bytes = HTML(
        string=html_content, base_url=str(static_directory)
    ).write_pdf()

    character = report["character"]
    slug = _slugify(str(character.get("name") or ""), f"personagem_{character_id}")
    filename = f"personagem_{slug}_{character_id}.pdf"

    response = Response(pdf_bytes, mimetype="application/pdf")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.headers["Content-Length"] = str(len(pdf_bytes))
    return response
