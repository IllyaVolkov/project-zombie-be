To initiate data, run:

```bash
python manage.py migrate
python manage.py loaddata genders resources
python manage.py collectstatic --no-input
```

To access django admin, create superuser:

```bash
python manage.py createsuperuser
```

To run django tests (DATABASE_URL env must be set):

```bash
python manage.py test
```

Automatic docs are available under `/swagger` path