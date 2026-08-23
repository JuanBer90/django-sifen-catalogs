from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from django_sifen_catalogs.csv_reader import read_locations_csv
from django_sifen_catalogs.models import City, Department, District, Neighborhood

DEFAULT_DATA_FILE = (
    Path(__file__).resolve().parents[2] / "data" / "locations.csv"
)


class Command(BaseCommand):
    help = _(
        "Import departments, districts, cities, and neighborhoods from locations.csv "
        "idempotently."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            dest="file_path",
            help=_(
                "Path to the CSV file to import. Defaults to the bundled file at "
                "django_sifen_catalogs/data/locations.csv"
            ),
        )

    def handle(self, *args, **options):
        file_option = options.get("file_path")

        if file_option:
            data_file = Path(file_option)
            if not data_file.is_absolute():
                data_file = Path.cwd() / data_file
        else:
            data_file = DEFAULT_DATA_FILE

        if not data_file.exists():
            raise CommandError(_("CSV file not found: %(path)s") % {"path": data_file})

        try:
            records = list(read_locations_csv(data_file))
        except CommandError:
            raise
        except OSError as exc:
            raise CommandError(
                _("Could not read CSV file: %(path)s") % {"path": data_file}
            ) from exc

        if not records:
            raise CommandError(_("The CSV file has no data rows."))

        department_created_codes: set[int] = set()
        department_updated_codes: set[int] = set()
        district_created_codes: set[int] = set()
        district_updated_codes: set[int] = set()
        city_created_codes: set[int] = set()
        city_updated_codes: set[int] = set()
        neighborhood_created_codes: set[int] = set()
        neighborhood_updated_codes: set[int] = set()

        with transaction.atomic():
            for record in records:
                department, department_created = Department.objects.update_or_create(
                    sifen_code=record.department_code,
                    defaults={"name": record.department_name},
                )
                if department_created:
                    department_created_codes.add(record.department_code)
                else:
                    department_updated_codes.add(record.department_code)

                district, district_created = District.objects.update_or_create(
                    sifen_code=record.district_code,
                    defaults={
                        "name": record.district_name,
                        "department": department,
                    },
                )
                if district_created:
                    district_created_codes.add(record.district_code)
                else:
                    district_updated_codes.add(record.district_code)

                city, city_created = City.objects.update_or_create(
                    sifen_code=record.city_code,
                    defaults={
                        "name": record.city_name,
                        "district": district,
                    },
                )
                if city_created:
                    city_created_codes.add(record.city_code)
                else:
                    city_updated_codes.add(record.city_code)

                if record.neighborhood_code is not None:
                    _neighborhood, neighborhood_created = (
                        Neighborhood.objects.update_or_create(
                            sifen_code=record.neighborhood_code,
                            defaults={
                                "name": record.neighborhood_name,
                                "city": city,
                            },
                        )
                    )
                    if neighborhood_created:
                        neighborhood_created_codes.add(record.neighborhood_code)
                    else:
                        neighborhood_updated_codes.add(record.neighborhood_code)

        self.stdout.write(self.style.SUCCESS(_("File: %(path)s") % {"path": data_file}))
        self.stdout.write(
            self.style.SUCCESS(
                _("Rows processed: %(count)s") % {"count": len(records)}
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                _("Departments created: %(created)s | updated: %(updated)s")
                % {
                    "created": len(department_created_codes),
                    "updated": len(department_updated_codes),
                }
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                _("Districts created: %(created)s | updated: %(updated)s")
                % {
                    "created": len(district_created_codes),
                    "updated": len(district_updated_codes),
                }
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                _("Cities created: %(created)s | updated: %(updated)s")
                % {
                    "created": len(city_created_codes),
                    "updated": len(city_updated_codes),
                }
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                _("Neighborhoods created: %(created)s | updated: %(updated)s")
                % {
                    "created": len(neighborhood_created_codes),
                    "updated": len(neighborhood_updated_codes),
                }
            )
        )
