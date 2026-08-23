from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from django_sifen_catalogs.models import City, Department, District, Neighborhood


class LocationModelTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(
            sifen_code=1,
            name="CAPITAL",
        )
        self.district = District.objects.create(
            sifen_code=10,
            name="ASUNCION (DISTRITO)",
            department=self.department,
        )
        self.city = City.objects.create(
            sifen_code=100,
            name="ASUNCION (DISTRITO)",
            district=self.district,
        )

    def test_department_sifen_code_is_unique(self):
        with self.assertRaises(IntegrityError):
            Department.objects.create(sifen_code=1, name="Duplicado")

    def test_district_sifen_code_is_unique(self):
        with self.assertRaises(IntegrityError):
            District.objects.create(
                sifen_code=10,
                name="Duplicado",
                department=self.department,
            )

    def test_city_sifen_code_is_unique(self):
        with self.assertRaises(IntegrityError):
            City.objects.create(
                sifen_code=100,
                name="Duplicado",
                district=self.district,
            )

    def test_neighborhood_sifen_code_is_unique(self):
        Neighborhood.objects.create(
            sifen_code=1000,
            name="MANORA",
            city=self.city,
        )

        with self.assertRaises(IntegrityError):
            Neighborhood.objects.create(
                sifen_code=1000,
                name="Duplicado",
                city=self.city,
            )

    def test_location_relationships_are_protected(self):
        Neighborhood.objects.create(
            sifen_code=1000,
            name="MANORA",
            city=self.city,
        )

        with self.assertRaises(ProtectedError):
            self.city.delete()

        with self.assertRaises(ProtectedError):
            self.district.delete()

        with self.assertRaises(ProtectedError):
            self.department.delete()

    def test_model_str_values_exclude_sifen_codes(self):
        neighborhood = Neighborhood.objects.create(
            sifen_code=1000,
            name="MANORA",
            city=self.city,
        )

        self.assertEqual(str(self.department), "CAPITAL")
        self.assertEqual(str(self.district), "ASUNCION (DISTRITO)")
        self.assertEqual(str(self.city), "ASUNCION (DISTRITO) — ASUNCION (DISTRITO)")
        self.assertEqual(str(neighborhood), "MANORA — ASUNCION (DISTRITO)")
