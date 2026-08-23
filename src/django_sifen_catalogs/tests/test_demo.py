from django.apps import apps
from django.core.management import call_command


def test_demo_system_check():
    call_command("check")


def test_address_admin_nested_dependencies():
    from demo.admin import AddressAdmin

    assert AddressAdmin.autocomplete_fields == (
        "department",
        "district",
        "city",
        "neighborhood",
    )
    assert AddressAdmin.autocomplete_dependencies == {
        "district": "department",
        "city": "district",
        "neighborhood": "city",
    }


def test_address_foreign_keys_point_to_locations_models():
    from demo.models import Address

    department_field = Address._meta.get_field("department")
    district_field = Address._meta.get_field("district")
    city_field = Address._meta.get_field("city")
    neighborhood_field = Address._meta.get_field("neighborhood")

    assert department_field.remote_field.model == apps.get_model("locations", "Department")
    assert district_field.remote_field.model == apps.get_model("locations", "District")
    assert city_field.remote_field.model == apps.get_model("locations", "City")
    assert neighborhood_field.remote_field.model == apps.get_model("locations", "Neighborhood")

    assert district_field.remote_field.model._meta.get_field("department").remote_field.model == (
        department_field.remote_field.model
    )
    assert city_field.remote_field.model._meta.get_field("district").remote_field.model == (
        district_field.remote_field.model
    )
    assert neighborhood_field.remote_field.model._meta.get_field("city").remote_field.model == (
        city_field.remote_field.model
    )
