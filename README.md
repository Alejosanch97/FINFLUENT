# FinFluent

Educación financiera en inglés (CLIL) para grados 6° a 11°. Un grado = 4 periodos.
React + Vite en el front, Flask + SQLAlchemy en el back, PostgreSQL (Supabase) como base de datos y Render para publicar.

## Roles

| Rol | Qué hace |
| --- | --- |
| `SUPERADMIN` | Crea colegios, define cupos por grado y crea el admin de cada colegio. |
| `ADMIN` | Admin de **un** colegio: crea estudiantes pegando 3 listas (nombres, usuarios, claves) y ve el progreso y las respuestas por grado. |
| `STUDENT` | Ve solo el curso de su grado. Al completar los 4 periodos recibe el diploma con el nombre de su colegio. |

## Probar en local

No necesitas instalar Postgres: sin `DATABASE_URL` se usa un archivo `local.sqlite`.

```bash
# 1) dependencias
pipenv install
npm install

# 2) variables (el zip ya trae un .env de desarrollo; si no existe:)
cp .env.example .env

# 3) base de datos + usuarios de prueba
pipenv run upgrade            # crea las tablas
pipenv run flask seed         # crea el super admin del .env
pipenv run flask seed-demo    # colegio demo, un admin y un estudiante por grado

# 4) dos terminales
pipenv run start              # backend  -> http://localhost:3001
npm run dev                   # frontend -> http://localhost:3000
```

Usuarios de prueba:

| Usuario | Clave | Rol |
| --- | --- | --- |
| `superadmin` | la de `SUPERADMIN_PASSWORD` en `.env` | Super admin |
| `admin.demo` | `demo1234` | Admin del colegio demo |
| `demo6` … `demo11` | `1234` | Estudiante de cada grado |

Otros comandos: `pipenv run flask set-password USUARIO CLAVE`.

## Dónde está cada cosa

```
src/api/models.py         tablas (colegios, cupos, usuarios, progreso, juegos)
src/api/routes.py         login y progreso          /api/auth/*  /api/progress
src/api/games.py          juegos multijugador       /api/games/<familia>/<accion>
src/api/admin_routes.py   admin del colegio         /api/admin/*
src/api/super_routes.py   super admin               /api/super/*
src/front/api.js          cliente de la API (token, sesión)
src/front/finFetch.js     puente: las actividades siguen llamando como en Apps Script
src/front/progressSync.js cola de guardado con reintentos + copia en localStorage
src/front/persist.js      recuerda la actividad abierta y lo que se estaba escribiendo
src/front/courses.js      mapa de grados y periodos (dashboard, home, admin, diploma)
src/front/pages/          Home, Dashboard, AdminPanel, SuperAdmin y los 24 periodos
```

El curso demo de 6 semanas (`Semana1…6.jsx`) se conserva en el repo pero está desactivado
(ver el bloque comentado al inicio de `Dashboard.jsx`).

## Producción

Un solo servicio web en Render: `render_build.sh` compila el front, crea/actualiza las tablas y
crea el super admin; Flask sirve la API y el front desde el mismo dominio.
Variables que se ponen a mano en Render: `DATABASE_URL` (Supabase, *Session pooler*),
`SUPERADMIN_USER`, `SUPERADMIN_PASSWORD`, `SUPERADMIN_NAME`.
