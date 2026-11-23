"""
Autenticación con JWT y permisos por rol.
  SUPERADMIN -> dueño de la plataforma: crea colegios, cupos y admins.
  ADMIN      -> admin de UN colegio: crea estudiantes y ve su progreso.
  STUDENT    -> ve solo el curso de su grado.
"""
import os
from datetime import timedelta
from functools import wraps

from flask import request
from flask_jwt_extended import (create_access_token, get_jwt_identity,
                                verify_jwt_in_request)
from sqlalchemy import func
from werkzeug.security import check_password_hash, generate_password_hash

from api.models import db, User, School, ROLE_SUPER, ROLE_ADMIN, utcnow
from api.utils import APIException

# pbkdf2 (sin picos de memoria): aguanta 30 logins al tiempo en una instancia pequeña
HASH_METHOD = "pbkdf2:sha256:120000"
TZ_OFFSET_HOURS = int(os.getenv("TZ_OFFSET_HOURS", "-5"))


def hash_password(raw):
    return generate_password_hash(str(raw), method=HASH_METHOD)


def verify_password(hashed, raw):
    try:
        return check_password_hash(hashed, str(raw))
    except Exception:
        return False


def find_user_by_key(key):
    key = str(key or "").strip()
    if not key:
        return None
    return User.query.filter(func.lower(User.student_key) == key.lower()).first()


def make_token(user):
    return create_access_token(identity=str(user.id), additional_claims={"role": user.role})


def current_user():
    verify_jwt_in_request()
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.is_active:
        raise APIException("Your session is no longer valid. Log in again.", 401)
    if user.school_id and user.school and not user.school.is_active:
        raise APIException("Your school's access is paused. Talk to your teacher.", 401)
    return user


def auth_required(*roles):
    """@auth_required() cualquier usuario · @auth_required(ROLE_ADMIN, ROLE_SUPER) solo esos roles."""
    def deco(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = current_user()
            if roles and user.role not in roles:
                raise APIException("No autorizado.", 403)
            return fn(user, *args, **kwargs)
        return wrapper
    return deco


def admin_school(user):
    """Colegio sobre el que trabaja un admin. El super admin lo elige con ?school_id=."""
    if user.role == ROLE_SUPER:
        sid = request.args.get("school_id") or (request.get_json(silent=True) or {}).get("school_id")
        if not sid:
            raise APIException("Indica el colegio (school_id).", 400)
        school = db.session.get(School, int(sid))
    else:
        school = user.school
    if not school:
        raise APIException("Colegio no encontrado.", 404)
    return school


def touch_login(user):
    """Actualiza último ingreso y racha de días seguidos."""
    now = utcnow()
    last = user.last_login
    if last is not None:
        if last.tzinfo is None:
            last = last.replace(tzinfo=now.tzinfo)
        shift = timedelta(hours=TZ_OFFSET_HOURS)      # el "día" es el de Colombia, no el de UTC
        days = ((now + shift).date() - (last + shift).date()).days
        if days == 1:
            user.streak_days = (user.streak_days or 0) + 1
        elif days > 1:
            user.streak_days = 1
        elif not user.streak_days:
            user.streak_days = 1
    else:
        user.streak_days = 1
    user.last_login = now
