"""Convert an official DNIT/SIFEN geographic reference spreadsheet into package CSV."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path

from xlsx_reader import (
    SpreadsheetError,
    extract_catalog_metadata,
    find_header_mapping,
    find_header_row_index,
    read_xlsx_first_sheet_rows,
    to_int,
)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "django_sifen_catalogs"
    / "data"
    / "locations.csv"
)
DEFAULT_PROVENANCE = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "django_sifen_catalogs"
    / "data"
    / "PROVENANCE.md"
)

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

    def as_csv_row(self) -> list[str]:
        return [
            str(self.department_code),
            self.department_name,
            str(self.district_code),
            self.district_name,
            str(self.city_code),
            self.city_name,
            "" if self.neighborhood_code is None else str(self.neighborhood_code),
            self.neighborhood_name,
        ]


def _parse_optional_int(value: str, field_label: str) -> int | None:
    cleaned = (value or "").strip()
    if not cleaned:
        return None
    return to_int(cleaned, field_label)


def parse_spreadsheet(path: Path) -> tuple[list[LocationRecord], dict[str, str], int]:
    rows = read_xlsx_first_sheet_rows(path)
    if not rows:
        raise SpreadsheetError("The spreadsheet has no readable rows.")

    header_index = find_header_row_index(rows)
    mapping = find_header_mapping(rows[header_index])
    metadata = extract_catalog_metadata(rows, header_index)
    has_neighborhood_columns = "bar_codigo" in mapping and "bar_nombre" in mapping

    department_names: dict[int, str] = {}
    district_names: dict[tuple[int, int], str] = {}
    city_names: dict[tuple[int, int, int], str] = {}
    neighborhood_records: dict[int, tuple[str, int, int, int]] = {}
    records: list[LocationRecord] = []
    seen_rows: set[LocationRecord] = set()
    errors: list[str] = []

    for row_number, row in enumerate(rows[header_index + 1 :], start=header_index + 2):
        if not any((cell or "").strip() for cell in row):
            continue

        try:
            department_code = to_int(row[mapping["dep_codigo"]], "Department code")
            department_name = (row[mapping["dep_nombre"]] or "").strip()
            district_code = to_int(row[mapping["dis_codigo"]], "District code")
            district_name = (row[mapping["dis_nombre"]] or "").strip()
            city_code = to_int(row[mapping["ciu_codigo"]], "City code")
            city_name = (row[mapping["ciu_nombre"]] or "").strip()
            if has_neighborhood_columns:
                neighborhood_code = _parse_optional_int(
                    row[mapping["bar_codigo"]], "Neighborhood code"
                )
                neighborhood_name = (row[mapping["bar_nombre"]] or "").strip()
            else:
                neighborhood_code = None
                neighborhood_name = ""
        except (IndexError, ValueError, TypeError) as exc:
            errors.append(f"Row {row_number}: {exc}")
            continue

        if not department_name:
            errors.append(f"Row {row_number}: department is empty.")
            continue
        if not district_name:
            errors.append(f"Row {row_number}: district is empty.")
            continue
        if not city_name:
            errors.append(f"Row {row_number}: city is empty.")
            continue

        if (neighborhood_code is None) ^ (not neighborhood_name):
            errors.append(
                f"Row {row_number}: neighborhood code and name must both be "
                "present or both be empty."
            )
            continue

        existing_department_name = department_names.get(department_code)
        if existing_department_name and existing_department_name != department_name:
            errors.append(
                f"Row {row_number}: department {department_code} has inconsistent "
                f"names ({existing_department_name!r} vs {department_name!r})."
            )
        else:
            department_names[department_code] = department_name

        district_key = (district_code, department_code)
        existing_district_name = district_names.get(district_key)
        if existing_district_name and existing_district_name != district_name:
            errors.append(
                f"Row {row_number}: district {district_code} (department "
                f"{department_code}) has inconsistent names ({existing_district_name!r} "
                f"vs {district_name!r})."
            )
        else:
            district_names[district_key] = district_name

        city_key = (city_code, district_code, department_code)
        existing_city_name = city_names.get(city_key)
        if existing_city_name and existing_city_name != city_name:
            errors.append(
                f"Row {row_number}: city {city_code} (district {district_code}, "
                f"department {department_code}) has inconsistent names "
                f"({existing_city_name!r} vs {city_name!r})."
            )
        else:
            city_names[city_key] = city_name

        if neighborhood_code is not None:
            existing_neighborhood = neighborhood_records.get(neighborhood_code)
            neighborhood_context = (city_code, district_code, department_code)
            if existing_neighborhood:
                existing_name, existing_city, existing_district, existing_department = (
                    existing_neighborhood
                )
                if (
                    existing_name != neighborhood_name
                    or (
                        existing_city,
                        existing_district,
                        existing_department,
                    )
                    != neighborhood_context
                ):
                    errors.append(
                        f"Row {row_number}: neighborhood {neighborhood_code} has "
                        "data inconsistent with earlier rows."
                    )
            else:
                neighborhood_records[neighborhood_code] = (
                    neighborhood_name,
                    city_code,
                    district_code,
                    department_code,
                )

        record = LocationRecord(
            department_code=department_code,
            department_name=department_name,
            district_code=district_code,
            district_name=district_name,
            city_code=city_code,
            city_name=city_name,
            neighborhood_code=neighborhood_code,
            neighborhood_name=neighborhood_name,
        )
        if record in seen_rows:
            errors.append(f"Row {row_number}: duplicate row.")
            continue
        seen_rows.add(record)
        records.append(record)

    if errors:
        raise SpreadsheetError(
            "Errors while processing the spreadsheet:\n- " + "\n- ".join(errors)
        )

    records.sort(
        key=lambda item: (
            item.department_code,
            item.district_code,
            item.city_code,
            item.neighborhood_code if item.neighborhood_code is not None else -1,
        )
    )
    metadata["source_rows"] = str(len(records))
    return records, metadata, header_index


def write_csv(records: list[LocationRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(CSV_COLUMNS)
        for record in records:
            writer.writerow(record.as_csv_row())


def write_provenance(
    provenance_path: Path,
    source_file: Path,
    metadata: dict[str, str],
    record_counts: dict[str, int],
) -> None:
    catalog_date = metadata.get("catalog_date", "unknown")
    source_rows = metadata.get("source_rows", "unknown")

    content = f"""# SIFEN geographic catalog provenance

- **Distribution source:** DNIT Paraguay
- **DNIT source URL:** https://www.dnit.gov.py/web/e-kuatia/tablas-y-codificaciones
- **Catalog:** Código de Referencia Geográfica
- **Underlying geographic data:** INE Código Geográfico 2022
- **INE reference URL:** https://www.ine.gov.py/microdatos/codigo-geografico-2022.php
- **Original source format:** XLS/XLSX
- **Generated package format:** CSV (`locations.csv`)
- **Catalog/source date:** {catalog_date}
- **Generated from file:** `{source_file.name}`

## Notes

- This CSV is generated by `scripts/update_sifen_catalog.py`. Do not edit it manually.
- The official spreadsheet is maintainer input only and is not bundled in the wheel.
- The CSV preserves one row per official catalog entry ({source_rows} rows), including
  optional neighborhood columns when barrio data is present.
- The generated CSV preserves DNIT's official hierarchy and does not reinterpret
  geographic classifications. City/locality codes and names are kept exactly as published;
  neighborhood data is included only from the official barrio code/name columns.
- Record counts: {record_counts["departments"]} departments, {record_counts["districts"]} districts,
  {record_counts["cities"]} cities, {record_counts["neighborhoods"]} neighborhoods.
- This package repackages publicly available official catalog data for developer convenience.
  It is not affiliated with, endorsed by, or sponsored by DNIT or INE.

## Update workflow

1. Download the latest official DNIT geographic reference spreadsheet.
2. Run `python scripts/update_sifen_catalog.py /path/to/oficial.xlsx`.
3. Review the CSV diff and updated provenance metadata.
4. Release a new package version.
"""
    provenance_path.write_text(content, encoding="utf-8")


def summarize(records: list[LocationRecord]) -> dict[str, int]:
    departments = {record.department_code for record in records}
    districts = {(record.district_code, record.department_code) for record in records}
    cities = {(record.city_code, record.district_code, record.department_code) for record in records}
    neighborhoods = {
        record.neighborhood_code
        for record in records
        if record.neighborhood_code is not None
    }
    return {
        "departments": len(departments),
        "districts": len(districts),
        "cities": len(cities),
        "neighborhoods": len(neighborhoods),
        "csv_rows": len(records),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert an official DNIT/SIFEN geographic reference spreadsheet into "
            "the canonical CSV used by django-sifen-catalogs."
        )
    )
    parser.add_argument(
        "source_file",
        type=Path,
        help="Path to the official DNIT XLS/XLSX file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--provenance",
        type=Path,
        default=DEFAULT_PROVENANCE,
        help=f"Provenance markdown path (default: {DEFAULT_PROVENANCE}).",
    )
    args = parser.parse_args(argv)

    source_file = args.source_file.resolve()
    if not source_file.exists():
        print(f"Error: source file not found: {source_file}", file=sys.stderr)
        return 1

    try:
        records, metadata, header_index = parse_spreadsheet(source_file)
    except SpreadsheetError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    counts = summarize(records)
    write_csv(records, args.output.resolve())
    write_provenance(args.provenance.resolve(), source_file, metadata, counts)

    print(f"Source: {source_file}")
    print(f"Header row: {header_index + 1}")
    print(f"Output CSV: {args.output.resolve()}")
    print(f"Provenance: {args.provenance.resolve()}")
    print(
        "Counts: "
        f"{counts['departments']} departments, "
        f"{counts['districts']} districts, "
        f"{counts['cities']} cities, "
        f"{counts['neighborhoods']} neighborhoods "
        f"({counts['csv_rows']} CSV rows)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
