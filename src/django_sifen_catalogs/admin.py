from django.contrib import admin

from django_sifen_catalogs.models import City, Department, District, Neighborhood


class CatalogAdmin(admin.ModelAdmin):
    """Protect official catalog structure; allow toggling is_active only."""

    editable_fields = ("is_active",)
    list_editable = ("is_active",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return [
            field.name
            for field in self.model._meta.fields
            if field.name not in self.editable_fields
        ]

    def get_fields(self, request, obj=None):
        field_names = [
            field.name for field in self.model._meta.fields if field.name != "id"
        ]
        readonly_fields = [
            name for name in field_names if name not in self.editable_fields
        ]
        return readonly_fields + list(self.editable_fields)


@admin.register(Department)
class DepartmentAdmin(CatalogAdmin):
    list_display = ("sifen_code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "sifen_code")
    ordering = ("name",)


@admin.register(District)
class DistrictAdmin(CatalogAdmin):
    list_display = ("sifen_code", "name", "department", "is_active")
    list_filter = ("is_active", "department")
    search_fields = ("name", "sifen_code", "department__name")
    autocomplete_fields = ("department",)
    ordering = ("name",)


@admin.register(City)
class CityAdmin(CatalogAdmin):
    list_display = ("sifen_code", "name", "district", "is_active")
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "sifen_code",
        "district__name",
        "district__department__name",
    )
    autocomplete_fields = ("district",)
    ordering = ("name",)


@admin.register(Neighborhood)
class NeighborhoodAdmin(CatalogAdmin):
    list_display = ("sifen_code", "name", "city", "is_active")
    list_filter = ("is_active",)
    search_fields = (
        "name",
        "sifen_code",
        "city__name",
        "city__district__name",
        "city__district__department__name",
    )
    autocomplete_fields = ("city",)
    ordering = ("name",)
