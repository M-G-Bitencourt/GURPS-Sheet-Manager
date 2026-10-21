"""Trait endpoints: skills, spells, spell schools, advantages and disadvantages."""

from flask import Blueprint

from api.crud_routes import register_crud_routes

traits_blueprint = Blueprint("traits", __name__, url_prefix="/api")

TRAIT_RESOURCES = (
    "skills",
    "spells",
    "spell-classes",
    "difficulties",
    "advantages",
    "disadvantages",
    "additional-stats",
    "combat-effects",
)

for _resource_key in TRAIT_RESOURCES:
    register_crud_routes(traits_blueprint, _resource_key)
