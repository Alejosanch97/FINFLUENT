#!/usr/bin/env bash
# exit on error
set -o errexit

npm install
npm run build

pipenv install

pipenv run upgrade          # crea / actualiza las tablas en Supabase
pipenv run flask seed       # crea el super admin la primera vez
