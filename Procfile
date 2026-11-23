release: pipenv run upgrade
web: gunicorn wsgi --chdir ./src/ --workers 2 --threads 4 --timeout 60
