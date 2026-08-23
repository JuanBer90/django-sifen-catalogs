# django-sifen-catalogs

Official SIFEN geographic location catalogs for Django: departments, districts, cities, and neighborhoods in Paraguay.

The package ships a CSV catalog derived from DNIT's *Código de Referencia Geográfica* and provides Django models plus an idempotent import command. Runtime dependencies are limited to Django.

## Scope

This release covers **geographic locations only**:

`Department` → `District` → `City` → `Neighborhood`

Each level uses official SIFEN numeric codes (`sifen_code`). Neighborhood data is included when present in the official catalog; other catalog types remain out of scope.

Current bundled catalog counts: **18** departments, **272** districts, **6,766** cities/localities, **1,104** neighborhoods (**7,735** CSV rows).

## Geographic hierarchy

The package preserves the geographic classification published in the official
DNIT SIFEN catalog:

Department → District → City / Locality → Neighborhood

`City` represents the official **City / Locality** field from the DNIT catalog.
Some entries may have names that appear to describe neighborhoods or urban
subdivisions. These entries are intentionally preserved as City / Locality
records because their codes and classification are part of the official SIFEN
reference data.

`Neighborhood` records are created only when the official catalog provides
values in the corresponding neighborhood fields.

The package does not reinterpret or normalize the official geographic
classification.

## Installation

```bash
pip install django-sifen-catalogs
```

## Django setup

Add the app to `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    # ...
    "django_sifen_catalogs.apps.LocationsConfig",
]
```

Run migrations:

```bash
python manage.py migrate locations
```

Import the bundled catalog:

```bash
python manage.py import_sifen_locations
```

Import a custom CSV with the same columns:

```bash
python manage.py import_sifen_locations --file /path/to/locations.csv
```

### Import semantics

- Custom `--file` input is expected to follow the same column layout and
  integrity assumptions as the package's generated `locations.csv`.
- Import is upsert-only: it creates or updates rows from the CSV and does not
  remove catalog entries that disappear in a future DNIT release.
- Re-import updates official names and parent relationships, but preserves each
  row's current `is_active` value. New rows default to active.
- In dependent admin autocompletes, neighborhood choices may be empty when the
  selected official city/locality has no barrio rows in the DNIT catalog.

## Models

Hierarchy: `Department` → `District` → `City` → `Neighborhood`

| Model | Key fields |
|-------|------------|
| `Department` | `sifen_code`, `name`, `is_active` |
| `District` | `sifen_code`, `name`, `department`, `is_active` |
| `City` | `sifen_code`, `name`, `district`, `is_active` |
| `Neighborhood` | `sifen_code`, `name`, `city`, `is_active` |

Example:

```python
from django_sifen_catalogs.models import City, Department, District, Neighborhood

central = Department.objects.get(sifen_code=12)
lambare_district = District.objects.get(sifen_code=169)
lambare_city = City.objects.get(sifen_code=6106)
kennedy = Neighborhood.objects.get(sifen_code=179)
```

Each lookup is model-scoped. The same numeric value can appear at different
levels in the official DNIT catalog (for example, city code `1` and neighborhood
code `1` are different records in different tables).

Model `__str__` values use friendly names only (for example, `City — District`, `Neighborhood — City`). SIFEN codes are exposed in admin and search fields instead.

## Stable identifiers

Use `sifen_code` as the interoperable identifier for a specific catalog model.
Codes are unique within each model (`Department`, `District`, `City`,
`Neighborhood`), not globally across all location types. Always resolve a code
through the intended model, for example `City.objects.get(sifen_code=6107)` or
`Neighborhood.objects.get(sifen_code=1)`.

Local primary keys are not part of the public contract.

## App label compatibility

| Concept | Value |
|---------|-------|
| Python package | `django_sifen_catalogs` |
| Django app label | `locations` |
| Database tables | `locations_department`, `locations_district`, `locations_city`, `locations_neighborhood` |
| Foreign key strings | `"locations.City"`, `"locations.District"`, `"locations.Department"`, `"locations.Neighborhood"` |

The app label `locations` is kept for compatibility with existing integrations.

## Internationalization

Model, field, and import-command UI labels use Django i18n with English source strings. Spanish translations ship in `django_sifen_catalogs/locale/es/LC_MESSAGES/django.mo`.

The package respects the host project's `LANGUAGE_CODE` and `LocaleMiddleware`. It does not define its own language setting, and official DNIT catalog names stored in the database are never translated.

Maintainers can refresh translations with:

```bash
django-admin makemessages -l es
django-admin compilemessages -l es
```

## Catalog provenance and updates

Bundled data files:

- `django_sifen_catalogs/data/locations.csv`
- `django_sifen_catalogs/data/PROVENANCE.md`

The official DNIT XLS/XLSX spreadsheet is **not** included in the wheel. Maintainers regenerate the CSV with:

```bash
python scripts/update_sifen_catalog.py /path/to/oficial.xlsx
```

Workflow: download the latest official file → run the script → review the CSV diff → release a new package version. See `PROVENANCE.md` for source details and the non-endorsement note.

## Admin

Catalog admins protect official structure: add and delete are disabled,
`sifen_code`, names, and parent relationships are read-only, and only
`is_active` is editable (including from the changelist). The host project must
include `django.contrib.admin`.

## Optional integration: dependent admin autocomplete

If your project model stores a location hierarchy, you can wire dependent admin autocompletes with [django-admin-dependent-autocomplete](https://pypi.org/project/django-admin-dependent-autocomplete/) (optional; not a runtime dependency of this package):

```python
from django.contrib import admin
from django.db import models
from django_admin_dependent_autocomplete.admin import DependentAutocompleteAdminMixin

from django_sifen_catalogs.models import City, Department, District, Neighborhood


class Customer(models.Model):
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    district = models.ForeignKey(District, on_delete=models.PROTECT)
    city = models.ForeignKey(City, on_delete=models.PROTECT)
    neighborhood = models.ForeignKey(Neighborhood, on_delete=models.PROTECT, blank=True, null=True)


@admin.register(Customer)
class CustomerAdmin(DependentAutocompleteAdminMixin, admin.ModelAdmin):
    autocomplete_fields = ["district", "city", "neighborhood"]
    autocomplete_dependencies = {
        "district": "department",
        "city": "district",
        "neighborhood": "city",
    }
```

This package registers structure-protected catalog admins with `search_fields`
for `Department`, `District`, `City`, and `Neighborhood`.

## Demo

A minimal Django Admin demo lives in `testapp/` (development only; not shipped in the package wheel).

```bash
pip install -e ".[dev]"
python testapp/manage.py migrate
python testapp/manage.py import_sifen_locations
python testapp/manage.py create_demo_superuser
python testapp/manage.py runserver
```

Open http://127.0.0.1:8000/admin/ and sign in with `admin` / `admin`.

The demo registers structure-protected catalog admins for departments, districts,
cities/localities, and neighborhoods, plus an `Address` model that uses
[django-admin-dependent-autocomplete](https://pypi.org/project/django-admin-dependent-autocomplete/)
for nested location selection. Neighborhood autocomplete stays empty for
city/locality records that have no official barrio data in the DNIT catalog.

## Development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pytest
ruff check .
python -m build
twine check dist/*
```

## Requirements

- Python >= 3.8
- Django >= 3.2, < 6.0

## License

MIT. See [LICENSE](LICENSE).
