from django.db import models
from django.utils.translation import gettext_lazy as _


class Department(models.Model):
    sifen_code = models.PositiveIntegerField(
        unique=True,
        verbose_name=_("SIFEN code"),
    )
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")
        ordering = ["name"]

    def __str__(self):
        return self.name


class District(models.Model):
    sifen_code = models.PositiveIntegerField(
        unique=True,
        verbose_name=_("SIFEN code"),
    )
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="districts",
        verbose_name=_("Department"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name = _("District")
        verbose_name_plural = _("Districts")
        ordering = ["name"]

    def __str__(self):
        return self.name


class City(models.Model):
    sifen_code = models.PositiveIntegerField(
        unique=True,
        verbose_name=_("SIFEN code"),
    )
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    district = models.ForeignKey(
        District,
        on_delete=models.PROTECT,
        related_name="cities",
        verbose_name=_("District"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name = _("City / Locality")
        verbose_name_plural = _("Cities / Localities")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} — {self.district.name}"


class Neighborhood(models.Model):
    sifen_code = models.PositiveIntegerField(
        unique=True,
        verbose_name=_("SIFEN code"),
    )
    name = models.CharField(max_length=200, verbose_name=_("Name"))
    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        related_name="neighborhoods",
        verbose_name=_("City / Locality"),
    )
    is_active = models.BooleanField(default=True, verbose_name=_("Active"))

    class Meta:
        verbose_name = _("Neighborhood")
        verbose_name_plural = _("Neighborhoods")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} — {self.city.name}"
