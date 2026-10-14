"""Metadata endpoints consumed by the frontend to build forms and tables."""

from flask import Blueprint, jsonify

from api.resources import RELATIONS, RESOURCES

meta_blueprint = Blueprint("meta", __name__, url_prefix="/api")


def _column_payload(column) -> dict:
    return {
        "name": column.name,
        "label": column.label,
        "type": column.type,
        "required": column.required,
        "default": column.default,
        "options": list(column.options),
        "fk_resource": column.fk_resource,
        "fk_label": column.fk_label,
        "read_only": column.read_only,
        "multiline": column.multiline,
    }


def _resource_payload(resource) -> dict:
    return {
        "key": resource.key,
        "table": resource.table,
        "pk": resource.pk,
        "label": resource.label,
        "pk_generation": resource.pk_generation,
        "search_columns": list(resource.search_columns),
        "columns": [_column_payload(column) for column in resource.columns],
    }


def _relation_payload(relation) -> dict:
    item_resource = RESOURCES[relation.item_resource]
    return {
        "key": relation.key,
        "label": relation.label,
        "pk": relation.pk,
        "item_fk": relation.item_fk,
        "item_resource": relation.item_resource,
        "item_pk": item_resource.pk,
        "item_label": relation.item_label,
        "secondary_fk": relation.secondary_fk,
        "secondary_resource": relation.secondary_resource,
        "secondary_label": relation.secondary_label,
        "columns": [_column_payload(column) for column in relation.columns],
    }


@meta_blueprint.get("/schemas")
def schemas_view():
    return jsonify(
        {
            "resources": {
                key: _resource_payload(resource)
                for key, resource in RESOURCES.items()
            },
            "relations": {
                key: _relation_payload(relation)
                for key, relation in RELATIONS.items()
            },
        }
    )


@meta_blueprint.get("/health")
def health_view():
    return jsonify({"status": "ok"})
