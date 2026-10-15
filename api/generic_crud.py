"""Generic SQLite CRUD driven exclusively by the declarative registry."""

import sqlite3
from typing import Any, Dict, List

from api.errors import ApiError, ConflictError, NotFoundError
from api.resources import Column, Resource, find_column, get_resource
from database.connection import get_connection


def coerce_value(column: Column, value: Any) -> Any:
    """Validates and normalizes a single value according to its column type."""
    is_empty = value is None or (isinstance(value, str) and value.strip() == "")

    if is_empty:
        if column.required:
            raise ApiError(f"O campo '{column.label}' é obrigatório.")
        if column.type == "bool":
            return 0
        return None

    if column.type == "int":
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ApiError(f"O campo '{column.label}' deve ser um número inteiro.")

    if column.type == "float":
        try:
            return float(value)
        except (TypeError, ValueError):
            raise ApiError(f"O campo '{column.label}' deve ser um número.")

    if column.type == "bool":
        return 1 if value in (True, 1, "1", "true", "True", "on", "sim") else 0

    return str(value).strip()


def _writable_columns(resource: Resource) -> List[Column]:
    """Columns accepted from clients: declared, not read-only and not the primary key."""
    return [
        column
        for column in resource.columns
        if not column.read_only and column.name != resource.pk
    ]


def _select_columns(resource: Resource) -> str:
    names = [resource.pk] + [
        column.name for column in resource.columns if column.name != resource.pk
    ]
    return ", ".join(f'"{name}"' for name in names)


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _casefold(value: Any) -> str:
    """Normalizes a value for case-insensitive duplicate comparison."""
    return str(value).strip().casefold()


def ensure_unique_columns(
    connection: sqlite3.Connection,
    resource: Resource,
    values: Dict[str, Any],
    exclude_pk: Any = None,
) -> None:
    """Rejects values that would duplicate a declared unique column of the resource."""
    columns = [
        name for name in resource.unique_columns if values.get(name) not in (None, "")
    ]
    if not columns:
        return

    selected = ", ".join(f'"{name}"' for name in columns)
    query = f'SELECT {selected} FROM "{resource.table}"'
    parameters: List[Any] = []
    if exclude_pk is not None:
        query += f' WHERE "{resource.pk}" <> ?'
        parameters.append(exclude_pk)

    wanted = {name: _casefold(values[name]) for name in columns}
    for row in connection.execute(query, parameters):
        if all(_casefold(row[name]) == wanted[name] for name in columns):
            column = find_column(resource, columns[0])
            label = column.label if column else columns[0]
            raise ConflictError(
                f"Já existe um registro com o mesmo valor no campo '{label}'."
            )


def translate_integrity_error(resource: Resource, error: sqlite3.IntegrityError) -> ApiError:
    message = str(error)

    if "UNIQUE constraint failed" in message:
        return ConflictError("Já existe um registro com esses valores.")

    if "FOREIGN KEY constraint failed" in message:
        hint = resource.delete_blocked_hint
        if hint:
            return ConflictError(
                f"Operação bloqueada: {hint} Remova os vínculos antes de excluir."
            )
        return ConflictError(
            "Referência inválida: o registro informado não existe ou está em uso."
        )

    if "NOT NULL constraint failed" in message:
        raw_column = message.split(":")[-1].strip().split(".")[-1]
        column = find_column(resource, raw_column)
        label = column.label if column else raw_column
        return ApiError(f"O campo '{label}' é obrigatório.")

    return ConflictError(f"Operação recusada pelo banco de dados: {message}")


def list_rows(resource_key: str) -> List[Dict[str, Any]]:
    """Returns every row of a resource ordered by its declared ordering."""
    resource = get_resource(resource_key)
    query = f'SELECT {_select_columns(resource)} FROM "{resource.table}"'
    if resource.order_by:
        query += f" ORDER BY {resource.order_by}"

    connection = get_connection()
    try:
        rows = connection.execute(query).fetchall()
    finally:
        connection.close()

    return [_row_to_dict(row) for row in rows]


def get_row(resource_key: str, primary_key: Any) -> Dict[str, Any]:
    """Fetches a single row by primary key or raises a 404 domain error."""
    resource = get_resource(resource_key)
    query = (
        f'SELECT {_select_columns(resource)} FROM "{resource.table}" '
        f'WHERE "{resource.pk}" = ?'
    )

    connection = get_connection()
    try:
        row = connection.execute(query, (primary_key,)).fetchone()
    finally:
        connection.close()

    if row is None:
        raise NotFoundError(
            f"{resource.label}: registro {primary_key} não encontrado."
        )
    return _row_to_dict(row)


def create_row(resource_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts a new row after validating every declared column."""
    resource = get_resource(resource_key)
    values: Dict[str, Any] = {}

    for column in _writable_columns(resource):
        if column.name in payload:
            values[column.name] = coerce_value(column, payload[column.name])
        elif column.required:
            raise ApiError(f"O campo '{column.label}' é obrigatório.")
        elif column.default is not None:
            values[column.name] = column.default

    connection = get_connection()
    try:
        ensure_unique_columns(connection, resource, values)

        if resource.pk_generation == "max_plus_one":
            next_pk = connection.execute(
                f'SELECT COALESCE(MAX("{resource.pk}"), 0) + 1 FROM "{resource.table}"'
            ).fetchone()[0]
            values[resource.pk] = next_pk

        if values:
            column_names = list(values.keys())
            quoted = ", ".join(f'"{name}"' for name in column_names)
            placeholders = ", ".join("?" for _ in column_names)
            query = (
                f'INSERT INTO "{resource.table}" ({quoted}) VALUES ({placeholders})'
            )
            cursor = connection.execute(query, [values[name] for name in column_names])
        else:
            cursor = connection.execute(f'INSERT INTO "{resource.table}" DEFAULT VALUES')

        connection.commit()
        new_pk = values.get(resource.pk, cursor.lastrowid)
    except sqlite3.IntegrityError as error:
        raise translate_integrity_error(resource, error) from error
    finally:
        connection.close()

    return get_row(resource_key, new_pk)


def update_row(
    resource_key: str, primary_key: Any, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """Updates the provided columns of an existing row."""
    resource = get_resource(resource_key)
    writable = {column.name: column for column in _writable_columns(resource)}

    updates: Dict[str, Any] = {}
    for name, value in payload.items():
        column = writable.get(name)
        if column is not None:
            updates[name] = coerce_value(column, value)

    if not updates:
        return get_row(resource_key, primary_key)

    assignments = ", ".join(f'"{name}" = ?' for name in updates)
    query = (
        f'UPDATE "{resource.table}" SET {assignments} '
        f'WHERE "{resource.pk}" = ?'
    )
    parameters = list(updates.values()) + [primary_key]

    connection = get_connection()
    try:
        ensure_unique_columns(connection, resource, updates, exclude_pk=primary_key)

        cursor = connection.execute(query, parameters)
        connection.commit()
        if cursor.rowcount == 0:
            raise NotFoundError(
                f"{resource.label}: registro {primary_key} não encontrado."
            )
    except sqlite3.IntegrityError as error:
        raise translate_integrity_error(resource, error) from error
    finally:
        connection.close()

    return get_row(resource_key, primary_key)


def delete_row(resource_key: str, primary_key: Any) -> None:
    """Deletes a row by primary key, translating constraint violations."""
    resource = get_resource(resource_key)
    query = f'DELETE FROM "{resource.table}" WHERE "{resource.pk}" = ?'

    connection = get_connection()
    try:
        cursor = connection.execute(query, (primary_key,))
        connection.commit()
        if cursor.rowcount == 0:
            raise NotFoundError(
                f"{resource.label}: registro {primary_key} não encontrado."
            )
    except sqlite3.IntegrityError as error:
        raise translate_integrity_error(resource, error) from error
    finally:
        connection.close()
