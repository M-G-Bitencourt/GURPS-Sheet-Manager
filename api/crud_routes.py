"""Reusable route registration for registry-driven resources."""

from flask import Blueprint, jsonify, request

from api.generic_crud import create_row, delete_row, get_row, list_rows, update_row


def register_crud_routes(blueprint: Blueprint, resource_key: str) -> None:
    """Attaches the five REST verbs for a single declarative resource."""
    endpoint = resource_key.replace("-", "_")

    @blueprint.get(f"/{resource_key}", endpoint=f"list_{endpoint}")
    def list_view():
        return jsonify(list_rows(resource_key))

    @blueprint.post(f"/{resource_key}", endpoint=f"create_{endpoint}")
    def create_view():
        payload = request.get_json(silent=True) or {}
        return jsonify(create_row(resource_key, payload)), 201

    @blueprint.get(f"/{resource_key}/<int:primary_key>", endpoint=f"get_{endpoint}")
    def get_view(primary_key: int):
        return jsonify(get_row(resource_key, primary_key))

    @blueprint.put(f"/{resource_key}/<int:primary_key>", endpoint=f"update_{endpoint}")
    def update_view(primary_key: int):
        payload = request.get_json(silent=True) or {}
        return jsonify(update_row(resource_key, primary_key, payload))

    @blueprint.delete(f"/{resource_key}/<int:primary_key>", endpoint=f"delete_{endpoint}")
    def delete_view(primary_key: int):
        delete_row(resource_key, primary_key)
        return "", 204
