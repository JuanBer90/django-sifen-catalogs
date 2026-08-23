from django.contrib import admin
from django_admin_dependent_autocomplete.admin import DependentAutocompleteAdminMixin

from demo.models import Address


@admin.register(Address)
class AddressAdmin(DependentAutocompleteAdminMixin, admin.ModelAdmin):
    list_display = ("label", "department", "district", "city", "neighborhood")
    autocomplete_fields = ("department", "district", "city", "neighborhood")
    autocomplete_dependencies = {
        "district": "department",
        "city": "district",
        "neighborhood": "city",
    }
