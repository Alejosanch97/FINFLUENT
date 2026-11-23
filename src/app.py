"""
FINFLUENT · arranque del servidor: base de datos, JWT, rutas /api y el front compilado (dist).
"""
import os
from datetime import timedelta

from flask import Flask, request, jsonify, send_from_directory
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from sqlalchemy import event
from sqlalchemy.engine import Engine
from werkzeug.exceptions import HTTPException

from api.utils import APIException, generate_sitemap
from api.models import db
from api.routes import api
from api.admin import setup_admin
from api.commands import setup_commands

ENV = "development" if os.getenv("FLASK_DEBUG") == "1" else "production"
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
static_file_dir = os.path.join(ROOT, 'dist')
app = Flask(__name__)
app.url_map.strict_slashes = False

# ---------------- Base de datos ----------------
# Producción: DATABASE_URL de Supabase (Postgres). Local sin DATABASE_URL: un archivo SQLite.
db_url = os.getenv("DATABASE_URL")
if db_url:
    # Driver explícito (psycopg2): SQLAlchemy 2.1+ ya no lo asume por defecto
    db_url = db_url.replace("postgres://", "postgresql://", 1)
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "pool_pre_ping": True,      # si Supabase cerró la conexión, se reconecta sola
        "pool_recycle": 280,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "5")),
    }
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(ROOT, "local.sqlite")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
MIGRATE = Migrate(app, db, compare_type=True)
db.init_app(app)


@event.listens_for(Engine, "connect")
def _sqlite_fk(dbapi_connection, _):
    # SQLite (solo local) necesita esto para respetar los ON DELETE CASCADE
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()


# ---------------- JWT ----------------
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY") or os.getenv("FLASK_APP_KEY") or "cambia-esta-llave-en-produccion"
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=int(os.getenv("JWT_DAYS", "7")))
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024
jwt = JWTManager(app)


def _jwt_error(message="Your session expired. Log in again."):
    return jsonify({"status": "error", "message": message, "auth": False}), 401


jwt.unauthorized_loader(lambda reason: _jwt_error())
jwt.invalid_token_loader(lambda reason: _jwt_error())
jwt.expired_token_loader(lambda header, payload: _jwt_error())
jwt.revoked_token_loader(lambda header, payload: _jwt_error())

# Flask-Admin (/admin) expone TODAS las tablas sin contraseña: solo en desarrollo.
if ENV == "development":
    setup_admin(app)
else:
    app.secret_key = os.environ.get('FLASK_APP_KEY', 'sample key')

setup_commands(app)
app.register_blueprint(api, url_prefix='/api')


# ---------------- Errores siempre en JSON ----------------
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    db.session.rollback()
    return jsonify(error.to_dict()), error.status_code


@app.errorhandler(Exception)
def handle_unexpected(error):
    if isinstance(error, HTTPException):
        if request.path.startswith("/api/"):
            return jsonify({"status": "error", "message": error.description}), error.code
        return error
    db.session.rollback()
    app.logger.exception(error)
    return jsonify({"status": "error", "message": "Server error. Try again."}), 500


# ---------------- Front compilado ----------------
@app.route('/')
def sitemap():
    if ENV == "development":
        return generate_sitemap(app)
    return _send('index.html')


@app.route('/<path:path>', methods=['GET'])
def serve_any_other_file(path):
    if path.startswith("api/"):
        return jsonify({"status": "error", "message": "Not found"}), 404
    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = 'index.html'
    return _send(path)


def _send(path):
    """Sirve dist/. Los archivos de /assets llevan hash en el nombre: se cachean 1 año
    y se entregan comprimidos (.gz generado en el build) para que carguen rápido en el colegio."""
    full = os.path.join(static_file_dir, path)
    gz = full + ".gz"
    if "gzip" in request.headers.get("Accept-Encoding", "") and os.path.isfile(gz):
        response = send_from_directory(static_file_dir, path + ".gz")
        response.headers["Content-Encoding"] = "gzip"
        response.headers["Vary"] = "Accept-Encoding"
        import mimetypes
        response.headers["Content-Type"] = mimetypes.guess_type(path)[0] or "application/octet-stream"
    else:
        response = send_from_directory(static_file_dir, path)
    if path.startswith("assets/"):
        response.cache_control.max_age = 31536000
        response.cache_control.public = True
        response.cache_control.immutable = True
    else:
        response.cache_control.no_cache = True
        response.cache_control.max_age = 0
    if path.endswith(".html"):
        response.headers["Content-Language"] = "en"     # ayuda a que el navegador no ofrezca traducir
    return response


if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3001))
    app.run(host='0.0.0.0', port=PORT, debug=True)
