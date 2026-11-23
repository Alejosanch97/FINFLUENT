"""
=====================================================================
 FINFLUENT · SUPER ADMIN   (/api/super/…)   solo rol SUPERADMIN

   GET    /super/schools                 todos los colegios con cupos, usados y admins
   POST   /super/schools                 crea colegio + cupos por grado + su admin
   PUT    /super/schools/<id>            edita datos, escudo, firma, cupos, activo
   DELETE /super/schools/<id>            borra un colegio SIN estudiantes
   POST   /super/schools/<id>/admins     agrega otro admin al colegio
   PUT    /super/users/<id>              cambia nombre / clave / activo de un admin
   DELETE /super/users/<id>              borra un admin
=====================================================================
"""
from flask import jsonify
from sqlalchemy import func

from api.admin_routes import KEY_RE, grade_counts
from api.auth import auth_required, hash_password
from api.models import (db, User, School, GradeQuota, GRADES, ROLE_ADMIN,
                        ROLE_STUDENT, ROLE_SUPER, iso)
from api.routes import api, body
from api.utils import APIException

MAX_LOGO_CHARS = 400_000     # ~300 KB de imagen en base64


def school_or_404(school_id):
    school = db.session.get(School, int(school_id))
    if not school:
        raise APIException("Colegio no encontrado.", 404)
    return school


def set_quotas(school, quotas):
    current = {q.grade: q for q in school.quotas}
    for g in GRADES:
        if str(g) not in (quotas or {}) and g not in (quotas or {}):
            continue
        raw = quotas.get(str(g), quotas.get(g))
        try:
            n = max(0, min(5000, int(raw or 0)))
        except Exception:
            raise APIException(f"Cupo no válido para grado {g}.", 400)
        if g in current:
            current[g].max_students = n
        else:
            school.quotas.append(GradeQuota(grade=g, max_students=n))


def apply_school_fields(school, p):
    if "name" in p:
        name = " ".join(str(p["name"] or "").split())[:160]
        if not name:
            raise APIException("El colegio necesita un nombre.", 400)
        school.name = name
    for field, size in (("city", 120), ("signer_name", 120), ("signer_role", 120)):
        if field in p:
            setattr(school, field, str(p[field] or "").strip()[:size])
    if "logo" in p:
        logo = str(p["logo"] or "")
        if len(logo) > MAX_LOGO_CHARS:
            raise APIException("El escudo es muy pesado. Usa una imagen más pequeña.", 400)
        school.logo = logo
    if "lock_periods" in p:
        school.lock_periods = bool(p["lock_periods"])
    if "is_active" in p:
        school.is_active = bool(p["is_active"])
    if "quotas" in p:
        set_quotas(school, p["quotas"] or {})


def new_admin(school, data):
    name = " ".join(str((data or {}).get("name") or "").split())[:160]
    key = str((data or {}).get("key") or "").strip()
    pw = str((data or {}).get("password") or "").strip()
    if not name or not KEY_RE.match(key) or len(pw) < 4:
        raise APIException("Admin: escribe nombre, usuario (sin espacios) y una clave de 4+ caracteres.", 400)
    if User.query.filter(func.lower(User.student_key) == key.lower()).first():
        raise APIException(f"El usuario \"{key}\" ya existe. Usa otro.", 400)
    admin = User(student_key=key, full_name=name, email=str((data or {}).get("email") or "")[:160],
                 password_hash=hash_password(pw), role=ROLE_ADMIN)
    school.users.append(admin)
    return admin


def school_payload(school):
    out = school.serialize()
    out["used"] = grade_counts(school.id)
    admins = User.query.filter_by(school_id=school.id, role=ROLE_ADMIN).order_by(User.id).all()
    out["admins"] = [{"id": a.id, "key": a.student_key, "name": a.full_name, "active": a.is_active,
                      "lastLogin": iso(a.last_login)} for a in admins]
    avg = (db.session.query(func.avg(User.progress_total))
           .filter(User.school_id == school.id, User.role == ROLE_STUDENT).scalar())
    out["avg_progress"] = round(float(avg or 0))
    return out


@api.route('/super/schools', methods=['GET'])
@auth_required(ROLE_SUPER)
def super_list_schools(user):
    schools = School.query.order_by(School.name).all()
    return jsonify({"status": "success", "schools": [school_payload(s) for s in schools]}), 200


@api.route('/super/schools', methods=['POST'])
@auth_required(ROLE_SUPER)
def super_create_school(user):
    p = body()
    school = School(name="")
    db.session.add(school)
    apply_school_fields(school, {"name": p.get("name"), **{k: p[k] for k in
                        ("city", "signer_name", "signer_role", "logo", "lock_periods", "quotas") if k in p}})
    if p.get("admin"):
        new_admin(school, p["admin"])
    db.session.commit()
    return jsonify({"status": "success", "school": school_payload(school)}), 201


@api.route('/super/schools/<int:school_id>', methods=['PUT'])
@auth_required(ROLE_SUPER)
def super_update_school(user, school_id):
    school = school_or_404(school_id)
    apply_school_fields(school, body())
    db.session.commit()
    return jsonify({"status": "success", "school": school_payload(school)}), 200


@api.route('/super/schools/<int:school_id>', methods=['DELETE'])
@auth_required(ROLE_SUPER)
def super_delete_school(user, school_id):
    school = school_or_404(school_id)
    if User.query.filter_by(school_id=school.id, role=ROLE_STUDENT).count():
        raise APIException("Este colegio tiene estudiantes. Desactívalo en vez de borrarlo "
                           "(o borra primero sus estudiantes).", 400)
    db.session.delete(school)
    db.session.commit()
    return jsonify({"status": "success"}), 200


@api.route('/super/schools/<int:school_id>/admins', methods=['POST'])
@auth_required(ROLE_SUPER)
def super_add_admin(user, school_id):
    school = school_or_404(school_id)
    new_admin(school, body())
    db.session.commit()
    return jsonify({"status": "success", "school": school_payload(school)}), 201


@api.route('/super/users/<int:user_id>', methods=['PUT'])
@auth_required(ROLE_SUPER)
def super_update_user(user, user_id):
    target = db.session.get(User, user_id)
    if not target or target.role != ROLE_ADMIN:
        raise APIException("Admin no encontrado.", 404)
    p = body()
    if p.get("name"):
        target.full_name = " ".join(str(p["name"]).split())[:160]
    if p.get("password"):
        if len(str(p["password"]).strip()) < 4:
            raise APIException("La clave debe tener 4+ caracteres.", 400)
        target.password_hash = hash_password(str(p["password"]).strip())
    if "active" in p:
        target.is_active = bool(p["active"])
    db.session.commit()
    return jsonify({"status": "success", "school": school_payload(target.school)}), 200


@api.route('/super/users/<int:user_id>', methods=['DELETE'])
@auth_required(ROLE_SUPER)
def super_delete_user(user, user_id):
    target = db.session.get(User, user_id)
    if not target or target.role != ROLE_ADMIN:
        raise APIException("Admin no encontrado.", 404)
    school = target.school
    db.session.delete(target)
    db.session.commit()
    return jsonify({"status": "success", "school": school_payload(school)}), 200
