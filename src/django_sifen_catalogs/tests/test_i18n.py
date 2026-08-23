from django.core.management import call_command
from django.test import TestCase
from django.utils.translation import activate, deactivate

from django_sifen_catalogs.models import City, Department, District, Neighborhood


class LocationTranslationTests(TestCase):
    def tearDown(self):
        deactivate()

    def test_english_model_verbose_names(self):
        activate("en")
        self.assertEqual(str(Department._meta.verbose_name), "Department")
        self.assertEqual(str(District._meta.verbose_name), "District")
        self.assertEqual(str(City._meta.verbose_name), "City / Locality")
        self.assertEqual(str(Neighborhood._meta.verbose_name), "Neighborhood")

    def test_spanish_model_verbose_names(self):
        activate("es")
        self.assertEqual(str(Department._meta.verbose_name), "Departamento")
        self.assertEqual(str(District._meta.verbose_name), "Distrito")
        self.assertEqual(str(City._meta.verbose_name), "Ciudad / Localidad")
        self.assertEqual(str(Neighborhood._meta.verbose_name), "Barrio")

    def test_catalog_names_are_not_translated(self):
        activate("es")
        call_command("import_sifen_locations")

        department = Department.objects.get(sifen_code=1)
        self.assertEqual(department.name, "CAPITAL")
