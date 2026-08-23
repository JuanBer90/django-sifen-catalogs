"""Read canonical SIFEN location CSV data (stdlib only)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

from django.core.management.base import CommandError

CSV_COLUMNS = [
    "department_code",
    "department_name",
    "district_code",
    "district_name",
    "city_code",
    "city_name",
    "neighborhood_code",
    "neighborhood_name",
]


@dataclass(frozen=True)
class LocationRecord:
    department_code: int
    department_name: str
    district_code: int
    district_name: str
    city_code: int
    city_name: str
    neighborhood_code: int | None
    neighborhood_name: str


def to_int(value: str, field_label: str) -> int:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{field_label} is empty")
    digits = re.sub(r"[^\d]", "", cleaned)
    if not digits:
        raise ValueError(f"{field_label} is invalid: {value!r}")
    return int(digits)


def _parse_optional_int(value: str, field_label: str) -> int | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    return to_int(cleaned, field_label)


def _validate_headers(fieldnames: Sequence[str] | None) -> None:
    if not fieldnames:
        raise CommandError("The CSV file has no headers.")

    missing = [column for column in CSV_COLUMNS if column not in fieldnames]
    if missing:
        raise CommandError(
            "The CSV file is missing required columns. "
            f"Missing: {', '.join(missing)}."
        )


def read_locations_csv(path: Path) -> Iterator[LocationRecord]:
    if not path.exists():
        raise CommandError(f"CSV file not found: {path}")

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        _validate_headers(reader.fieldnames)

        for row_number, row in enumerate(reader, start=2):
            if row is None or not any((value or "").strip() for value in row.values()):
                continue

            try:
                department_code = to_int(row["department_code"], "department_code")
                department_name = (row["department_name"] or "").strip()
                district_code = to_int(row["district_code"], "district_code")
                district_name = (row["district_name"] or "").strip()
                city_code = to_int(row["city_code"], "city_code")
                city_name = (row["city_name"] or "").strip()
                neighborhood_code = _parse_optional_int(
                    row["neighborhood_code"], "neighborhood_code"
                )
                neighborhood_name = (row["neighborhood_name"] or "").strip()
            except (KeyError, ValueError, TypeError) as exc:
                raise CommandError(f"CSV row {row_number}: {exc}") from exc

            if not department_name:
                raise CommandError(f"CSV row {row_number}: department_name is empty.")
            if not district_name:
                raise CommandError(f"CSV row {row_number}: district_name is empty.")
            if not city_name:
                raise CommandError(f"CSV row {row_number}: city_name is empty.")
            if (neighborhood_code is None) ^ (not neighborhood_name):
                raise CommandError(
                    f"CSV row {row_number}: neighborhood_code and neighborhood_name "
                    "must both be present or both be empty."
                )

            yield LocationRecord(
                department_code=department_code,
                department_name=department_name,
                district_code=district_code,
                district_name=district_name,
                city_code=city_code,
                city_name=city_name,
                neighborhood_code=neighborhood_code,
                neighborhood_name=neighborhood_name,
            )


def load_locations_csv(path: Path) -> list[LocationRecord]:
    return list(read_locations_csv(path))
