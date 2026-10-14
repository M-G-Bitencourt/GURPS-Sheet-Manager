"""Flask application factory for the GURPS-Sheet-Manager."""

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from api.characters import characters_blueprint
from api.catalog import catalog_blueprint
from api.database import database_blueprint
from api.errors import ApiError
from api.export import export_blueprint
from api.meta import meta_blueprint
from api.traits import traits_blueprint
from database.migration import apply_migrations


def create_app() -> Flask:
    """Builds the Flask application and guarantees the schema is up to date."""
    apply_migrations()

    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["JSON_SORT_KEYS"] = False

    app.register_blueprint(meta_blueprint)
    app.register_blueprint(characters_blueprint)
    app.register_blueprint(catalog_blueprint)
    app.register_blueprint(traits_blueprint)
    app.register_blueprint(export_blueprint)
    app.register_blueprint(database_blueprint)

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unhandled error")
        return jsonify({"error": f"Erro interno do servidor: {error}"}), 500

    return app
