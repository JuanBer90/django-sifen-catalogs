import csv
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from django_sifen_catalogs.models import City, Department, District, Neighborhood

EXPECTED_COUNTS = (18, 272, 6766, 1104)
EXPECTED_CSV_ROWS = 7735
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
OFFICIAL_XLSX = FIXTURES_DIR / "referencia_geografica.xlsx"


class ImportSifenLocationsCommandTests(TestCase):
    @patch(
        "django_sifen_catalogs.management.commands.import_sifen_locations.read_locations_csv"
    )
    def test_import_command_loads_sample_rows(self, mock_read_csv):
        from django_sifen_catalogs.csv_reader import LocationRecord

        mock_read_csv.return_value = iter(
            [
                LocationRecord(
                    department_code=1,
                    department_name="Capital",
                    district_code=1,
                    district_name="Asunción",
                    city_code=1,
                    city_name="Asunción",
                    neighborhood_code=1,
                    neighborhood_name="Manora",
                )
            ]
        )

        call_command("import_sifen_locations")

        department = Department.objects.get(sifen_code=1)
        district = District.objects.get(sifen_code=1)
        city = City.objects.get(sifen_code=1)
        neighborhood = Neighborhood.objects.get(sifen_code=1)

        self.assertEqual(department.name, "Capital")
        self.assertEqual(district.name, "Asunción")
        self.assertEqual(district.department_id, department.id)
        self.assertEqual(city.name, "Asunción")
        self.assertEqual(city.district_id, district.id)
        self.assertEqual(neighborhood.name, "Manora")
        self.assertEqual(neighborhood.city_id, city.id)

    @patch(
        "django_sifen_catalogs.management.commands.import_sifen_locations.read_locations_csv"
    )
    def test_import_command_is_idempotent(self, mock_read_csv):
        from django_sifen_catalogs.csv_reader import LocationRecord

        mock_read_csv.return_value = [
            LocationRecord(
                department_code=1,
                department_name="Capital",
                district_code=1,
                district_name="Asunción",
                city_code=1,
                city_name="Asunción",
                neighborhood_code=None,
                neighborhood_name="",
            )
        ]

        call_command("import_sifen_locations")
        call_command("import_sifen_locations")

        self.assertEqual(Department.objects.count(), 1)
        self.assertEqual(District.objects.count(), 1)
        self.assertEqual(City.objects.count(), 1)
        self.assertEqual(Neighborhood.objects.count(), 0)

    def test_import_command_loads_packaged_csv_idempotently(self):
        call_command("import_sifen_locations")

        first_counts = (
            Department.objects.count(),
            District.objects.count(),
            City.objects.count(),
            Neighborhood.objects.count(),
        )
        self.assertEqual(first_counts, EXPECTED_COUNTS)
        self.assertFalse(District.objects.filter(department__isnull=True).exists())
        self.assertFalse(City.objects.filter(district__isnull=True).exists())
        self.assertFalse(Neighborhood.objects.filter(city__isnull=True).exists())

        call_command("import_sifen_locations")

        self.assertEqual(
            (
                Department.objects.count(),
                District.objects.count(),
                City.objects.count(),
                Neighborhood.objects.count(),
            ),
            first_counts,
        )

    def test_import_preserves_is_active_on_reimport(self):
        call_command("import_sifen_locations")

        department = Department.objects.get(sifen_code=12)
        city = City.objects.get(sifen_code=6106)
        neighborhood = Neighborhood.objects.get(sifen_code=179)

        department.is_active = False
        city.is_active = False
        neighborhood.is_active = False
        department.save(update_fields=["is_active"])
        city.save(update_fields=["is_active"])
        neighborhood.save(update_fields=["is_active"])

        call_command("import_sifen_locations")

        department.refresh_from_db()
        city.refresh_from_db()
        neighborhood.refresh_from_db()

        self.assertFalse(department.is_active)
        self.assertFalse(city.is_active)
        self.assertFalse(neighborhood.is_active)

    def test_import_command_rejects_malformed_csv(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            handle.write("department_code,department_name\n1,Capital\n")
            malformed_path = Path(handle.name)

        try:
            with self.assertRaises(CommandError):
                call_command("import_sifen_locations", file=str(malformed_path))
        finally:
            malformed_path.unlink(missing_ok=True)

    def test_csv_reader_rejects_invalid_row(self):
        from django_sifen_catalogs.csv_reader import read_locations_csv

        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "department_code",
                    "department_name",
                    "district_code",
                    "district_name",
                    "city_code",
                    "city_name",
                    "neighborhood_code",
                    "neighborhood_name",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "department_code": "1",
                    "department_name": "Capital",
                    "district_code": "1",
                    "district_name": "Asunción",
                    "city_code": "bad",
                    "city_name": "Asunción",
                    "neighborhood_code": "",
                    "neighborhood_name": "",
                }
            )
            malformed_path = Path(handle.name)

        try:
            with self.assertRaises(CommandError):
                list(read_locations_csv(malformed_path))
        finally:
            malformed_path.unlink(missing_ok=True)

    def test_csv_reader_rejects_mismatched_neighborhood_fields(self):
        from django_sifen_catalogs.csv_reader import read_locations_csv

        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "department_code",
                    "department_name",
                    "district_code",
                    "district_name",
                    "city_code",
                    "city_name",
                    "neighborhood_code",
                    "neighborhood_name",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "department_code": "1",
                    "department_name": "Capital",
                    "district_code": "1",
                    "district_name": "Asunción",
                    "city_code": "1",
                    "city_name": "Asunción",
                    "neighborhood_code": "1",
                    "neighborhood_name": "",
                }
            )
            malformed_path = Path(handle.name)

        try:
            with self.assertRaises(CommandError):
                list(read_locations_csv(malformed_path))
        finally:
            malformed_path.unlink(missing_ok=True)


class CatalogEquivalenceTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not OFFICIAL_XLSX.exists():
            cls.skip_reason = f"Official spreadsheet fixture missing: {OFFICIAL_XLSX}"
            return
        cls.skip_reason = None

        scripts_dir = Path(__file__).resolve().parents[3] / "scripts"
        sys.path.insert(0, str(scripts_dir))
        try:
            from update_sifen_catalog import parse_spreadsheet
        finally:
            sys.path.pop(0)

        cls._parse_spreadsheet = staticmethod(parse_spreadsheet)

    def setUp(self):
        if self.skip_reason:
            self.skipTest(self.skip_reason)

    def _import_records(self, records) -> None:
        for record in records:
            department, _ = Department.objects.update_or_create(
                sifen_code=record.department_code,
                defaults={"name": record.department_name},
            )
            district, _ = District.objects.update_or_create(
                sifen_code=record.district_code,
                defaults={
                    "name": record.district_name,
                    "department": department,
                },
            )
            city, _ = City.objects.update_or_create(
                sifen_code=record.city_code,
                defaults={
                    "name": record.city_name,
                    "district": district,
                },
            )
            if record.neighborhood_code is not None:
                Neighborhood.objects.update_or_create(
                    sifen_code=record.neighborhood_code,
                    defaults={
                        "name": record.neighborhood_name,
                        "city": city,
                    },
                )

    def _snapshot_models(self):
        departments = {
            (item.sifen_code, item.name)
            for item in Department.objects.select_related(None).order_by("sifen_code")
        }
        districts = {
            (
                item.sifen_code,
                item.name,
                item.department.sifen_code,
            )
            for item in District.objects.select_related("department").order_by(
                "sifen_code"
            )
        }
        cities = {
            (
                item.sifen_code,
                item.name,
                item.district.sifen_code,
                item.district.department.sifen_code,
            )
            for item in City.objects.select_related(
                "district", "district__department"
            ).order_by("sifen_code")
        }
        neighborhoods = {
            (
                item.sifen_code,
                item.name,
                item.city.sifen_code,
                item.city.district.sifen_code,
                item.city.district.department.sifen_code,
            )
            for item in Neighborhood.objects.select_related(
                "city", "city__district", "city__district__department"
            ).order_by("sifen_code")
        }
        return departments, districts, cities, neighborhoods

    def test_generated_csv_matches_official_spreadsheet_import(self):
        records, _, _ = self._parse_spreadsheet(OFFICIAL_XLSX)
        self._import_records(records)
        parsed_snapshot = self._snapshot_models()

        Neighborhood.objects.all().delete()
        City.objects.all().delete()
        District.objects.all().delete()
        Department.objects.all().delete()

        call_command("import_sifen_locations")
        csv_snapshot = self._snapshot_models()

        self.assertEqual(csv_snapshot, parsed_snapshot)
        self.assertEqual(
            (
                len(parsed_snapshot[0]),
                len(parsed_snapshot[1]),
                len(parsed_snapshot[2]),
                len(parsed_snapshot[3]),
            ),
            EXPECTED_COUNTS,
        )

    def test_lambare_barrio_kennedy_preserved_as_official_city_locality(self):
        records, _, _ = self._parse_spreadsheet(OFFICIAL_XLSX)
        kennedy_rows = [
            record
            for record in records
            if record.department_name == "CENTRAL"
            and record.district_name == "LAMBARE"
            and record.city_name == "BARRIO PTE.KENNEDY 1A."
        ]

        self.assertEqual(len(kennedy_rows), 1)
        self.assertEqual(kennedy_rows[0].city_code, 6107)
        self.assertIsNone(kennedy_rows[0].neighborhood_code)
        self.assertEqual(kennedy_rows[0].neighborhood_name, "")

        call_command("import_sifen_locations")

        city = City.objects.get(sifen_code=6107)
        self.assertEqual(city.name, "BARRIO PTE.KENNEDY 1A.")
        self.assertFalse(
            Neighborhood.objects.filter(sifen_code=6107).exists()
        )
        self.assertFalse(
            Neighborhood.objects.filter(name="BARRIO PTE.KENNEDY 1A.").exists()
        )

    def test_asuncion_official_barrio_data_creates_neighborhoods(self):
        records, _, _ = self._parse_spreadsheet(OFFICIAL_XLSX)
        manora_rows = [
            record
            for record in records
            if record.neighborhood_name == "MANORA"
        ]

        self.assertEqual(len(manora_rows), 1)
        self.assertEqual(manora_rows[0].neighborhood_code, 1)
        self.assertEqual(manora_rows[0].city_name, "ASUNCION (DISTRITO)")

        call_command("import_sifen_locations")

        neighborhood = Neighborhood.objects.get(sifen_code=1)
        self.assertEqual(neighborhood.name, "MANORA")
        self.assertEqual(neighborhood.city.name, "ASUNCION (DISTRITO)")

    def test_parse_spreadsheet_row_counts(self):
        records, _, _ = self._parse_spreadsheet(OFFICIAL_XLSX)
        self.assertEqual(len(records), EXPECTED_CSV_ROWS)
        neighborhood_count = sum(
            1 for record in records if record.neighborhood_code is not None
        )
        self.assertEqual(neighborhood_count, EXPECTED_COUNTS[3])
