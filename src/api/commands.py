"""
Comandos de consola:

  flask seed        crea el SUPER ADMIN si no existe (lee SUPERADMIN_USER / SUPERADMIN_PASSWORD
                    / SUPERADMIN_NAME del .env). Se ejecuta solo en cada deploy de Render.
  flask seed-demo   crea un colegio de prueba con un admin y un estudiante por grado.
  flask set-password USUARIO CLAVE   cambia la clave de cualquier usuario.
"""
import os

import click

from api.auth import find_user_by_key, hash_password
from api.models import (db, User, School, GradeQuota, GRADES, ROLE_ADMIN,
                        ROLE_STUDENT, ROLE_SUPER)


def setup_commands(app):

    @app.cli.command("seed")
    def seed():
        if User.query.filter_by(role=ROLE_SUPER).first():
            print("Super admin ya existe. Nada que hacer.")
            return
        key = os.getenv("SUPERADMIN_USER", "superadmin")
        pw = os.getenv("SUPERADMIN_PASSWORD")
        if not pw:
            print("⚠️  Falta SUPERADMIN_PASSWORD en las variables de entorno: no se creó el super admin.")
            return
        db.session.add(User(student_key=key, full_name=os.getenv("SUPERADMIN_NAME", "Super Admin"),
                            password_hash=hash_password(pw), role=ROLE_SUPER))
        db.session.commit()
        print(f"✅ Super admin creado: {key}")

    @app.cli.command("seed-demo")
    def seed_demo():
        if find_user_by_key("admin.demo"):
            print("El colegio demo ya existe.")
            return
        school = School(name="Colegio Demo FinFluent", city="Bogotá", signer_name="Rectoría", signer_role="Rector(a)")
        for g in GRADES:
            school.quotas.append(GradeQuota(grade=g, max_students=40))
        school.users.append(User(student_key="admin.demo", full_name="Admin Demo",
                                 password_hash=hash_password("demo1234"), role=ROLE_ADMIN))
        for g in GRADES:
            school.users.append(User(student_key=f"demo{g}", full_name=f"Estudiante Demo {g}",
                                     password_hash=hash_password("1234"), role=ROLE_STUDENT, grade=g, group_name=f"{g}A"))
        db.session.add(school)
        db.session.commit()
        print("✅ Colegio demo creado.")
        print("   Admin:        admin.demo / demo1234")
        print("   Estudiantes:  demo6, demo7, demo8, demo9, demo10, demo11  (clave 1234)")

    @app.cli.command("set-password")
    @click.argument("user_key")
    @click.argument("password")
    def set_password(user_key, password):
        user = find_user_by_key(user_key)
        if not user:
            print("Usuario no encontrado.")
            return
        user.password_hash = hash_password(password)
        db.session.commit()
        print(f"✅ Clave actualizada para {user.student_key}")
