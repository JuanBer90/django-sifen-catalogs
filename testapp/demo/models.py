from django.db import models


class Address(models.Model):
    label = models.CharField(max_length=200, blank=True)
    department = models.ForeignKey(
        "locations.Department",
        on_delete=models.PROTECT,
        related_name="demo_addresses",
    )
    district = models.ForeignKey(
        "locations.District",
        on_delete=models.PROTECT,
        related_name="demo_addresses",
    )
    city = models.ForeignKey(
        "locations.City",
        on_delete=models.PROTECT,
        related_name="demo_addresses",
    )
    neighborhood = models.ForeignKey(
        "locations.Neighborhood",
        on_delete=models.PROTECT,
        related_name="demo_addresses",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["label", "id"]

    def __str__(self) -> str:
        if self.label:
            return self.label
        return str(self.city)
