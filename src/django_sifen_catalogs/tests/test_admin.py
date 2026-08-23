from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from django_sifen_catalogs.admin import (
    CatalogAdmin,
    CityAdmin,
    DepartmentAdmin,
    DistrictAdmin,
    NeighborhoodAdmin,
)
from django_sifen_catalogs.models import City, Department, District, Neighborhood


class CatalogAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(
            sifen_code=1,
            name="CAPITAL",
        )
        cls.district = District.objects.create(
            sifen_code=10,
            name="ASUNCION (DISTRITO)",
            department=cls.department,
        )
        cls.city = City.objects.create(
            sifen_code=100,
            name="ASUNCION (DISTRITO)",
            district=cls.district,
        )
        cls.neighborhood = Neighborhood.objects.create(
            sifen_code=1000,
            name="MANORA",
            city=cls.city,
        )

    def setUp(self):
        self.factory = RequestFactory()
        self.request = self.factory.get("/admin/")
        self.request.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin",
        )

    def test_catalog_admins_are_registered(self):
        self.assertIsInstance(admin.site._registry[Department], DepartmentAdmin)
        self.assertIsInstance(admin.site._registry[District], DistrictAdmin)
        self.assertIsInstance(admin.site._registry[City], CityAdmin)
        self.assertIsInstance(admin.site._registry[Neighborhood], NeighborhoodAdmin)

    def test_add_and_delete_are_forbidden(self):
        for model in (Department, District, City, Neighborhood):
            model_admin = admin.site._registry[model]
            self.assertFalse(model_admin.has_add_permission(self.request))
            self.assertFalse(model_admin.has_delete_permission(self.request))
            self.assertFalse(
                model_admin.has_delete_permission(self.request, model.objects.first())
            )

    def test_change_is_allowed(self):
        for model in (Department, District, City, Neighborhood):
            model_admin = admin.site._registry[model]
            self.assertTrue(model_admin.has_change_permission(self.request))
            self.assertTrue(
                model_admin.has_change_permission(self.request, model.objects.first())
            )

    def test_structural_fields_are_read_only(self):
        cases = (
            (DepartmentAdmin, Department, self.department, ("sifen_code", "name")),
            (
                DistrictAdmin,
                District,
                self.district,
                ("sifen_code", "name", "department"),
            ),
            (CityAdmin, City, self.city, ("sifen_code", "name", "district")),
            (
                NeighborhoodAdmin,
                Neighborhood,
                self.neighborhood,
                ("sifen_code", "name", "city"),
            ),
        )

        for admin_class, model, instance, protected_fields in cases:
            with self.subTest(model=model.__name__):
                model_admin = admin_class(model, admin.site)
                readonly_fields = model_admin.get_readonly_fields(self.request, instance)
                for field_name in protected_fields:
                    self.assertIn(field_name, readonly_fields)
                self.assertNotIn("is_active", readonly_fields)

    def test_is_active_is_list_editable(self):
        for model in (Department, District, City, Neighborhood):
            with self.subTest(model=model.__name__):
                model_admin = admin.site._registry[model]
                self.assertEqual(model_admin.list_editable, ("is_active",))

    def test_is_active_is_last_on_change_form(self):
        cases = (
            (DepartmentAdmin, Department, ("sifen_code", "name", "is_active")),
            (
                DistrictAdmin,
                District,
                ("sifen_code", "name", "department", "is_active"),
            ),
            (CityAdmin, City, ("sifen_code", "name", "district", "is_active")),
            (
                NeighborhoodAdmin,
                Neighborhood,
                ("sifen_code", "name", "city", "is_active"),
            ),
        )

        for admin_class, model, expected_fields in cases:
            with self.subTest(model=model.__name__):
                model_admin = admin_class(model, admin.site)
                self.assertEqual(
                    model_admin.get_fields(self.request, model.objects.first()),
                    list(expected_fields),
                )

    def test_is_active_can_be_changed(self):
        self.department.is_active = False
        self.department.save(update_fields=["is_active"])
        self.department.refresh_from_db()
        self.assertFalse(self.department.is_active)

        self.department.is_active = True
        self.department.save(update_fields=["is_active"])
        self.department.refresh_from_db()
        self.assertTrue(self.department.is_active)

    def test_admin_search_still_works(self):
        cases = (
            (DepartmentAdmin, Department, "CAPITAL", self.department),
            (DistrictAdmin, District, "ASUNCION", self.district),
            (CityAdmin, City, "ASUNCION", self.city),
            (NeighborhoodAdmin, Neighborhood, "MANORA", self.neighborhood),
        )

        for admin_class, model, term, expected in cases:
            with self.subTest(model=model.__name__):
                model_admin = admin_class(model, admin.site)
                queryset = model.objects.all()
                results, _may_have_duplicates = model_admin.get_search_results(
                    self.request,
                    queryset,
                    term,
                )
                self.assertIn(expected, results)

    def test_catalog_admin_base_is_reused(self):
        for model_admin in (
            admin.site._registry[Department],
            admin.site._registry[District],
            admin.site._registry[City],
            admin.site._registry[Neighborhood],
        ):
            self.assertIsInstance(model_admin, CatalogAdmin)
