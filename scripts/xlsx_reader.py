"""Read DNIT/SIFEN geographic reference spreadsheets (XLSX only, stdlib)."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


class SpreadsheetError(Exception):
    """Raised when a spreadsheet cannot be parsed or has unexpected structure."""


def col_to_index(col_letters: str) -> int:
    col_letters = col_letters.upper()
    index = 0
    for char in col_letters:
        if not ("A" <= char <= "Z"):
            break
        index = index * 26 + (ord(char) - ord("A") + 1)
    return index


def parse_cell_ref(cell_ref: str) -> tuple[int, int]:
    match = re.match(r"^([A-Za-z]+)(\d+)$", cell_ref or "")
    if not match:
        return 0, 0
    return int(match.group(2)), col_to_index(match.group(1))


def normalize_header(value: str) -> str:
    normalized = (value or "").strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.translate(str.maketrans("áéíóúñ", "aeioun"))


def read_xlsx_first_sheet_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        raise SpreadsheetError(f"File not found: {path}")

    with zipfile.ZipFile(path, "r") as archive:
        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            shared_strings_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            namespace = {
                "s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
            }
            for shared_item in shared_strings_root.findall("s:si", namespace):
                texts = [
                    text.text or "" for text in shared_item.findall(".//s:t", namespace)
                ]
                shared_strings.append("".join(texts))

        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        namespace = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        sheet = workbook.find("s:sheets/s:sheet", namespace)
        if sheet is None:
            raise SpreadsheetError("No sheet found in the XLSX.")

        relationship_id = sheet.attrib.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        if not relationship_id:
            raise SpreadsheetError(
                "Could not resolve the main XLSX sheet (missing r:id)."
            )

        relationships = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relationships_namespace = {
            "r": "http://schemas.openxmlformats.org/package/2006/relationships"
        }
        target = None
        for relationship in relationships.findall("r:Relationship", relationships_namespace):
            if relationship.attrib.get("Id") == relationship_id:
                target = relationship.attrib.get("Target")
                break
        if not target:
            raise SpreadsheetError("Could not resolve the sheet XML file (rels).")

        sheet_path = f"xl/{target.lstrip('/')}"
        if sheet_path not in archive.namelist():
            raise SpreadsheetError(f"Expected sheet not found in the zip: {sheet_path}")

        worksheet = ET.fromstring(archive.read(sheet_path))
        rows: dict[int, dict[int, str]] = {}
        main_namespace = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
        for cell in worksheet.findall(f".//{{{main_namespace}}}c"):
            cell_ref = cell.attrib.get("r")
            row_number, column_number = parse_cell_ref(cell_ref)
            if row_number == 0 or column_number == 0:
                continue

            cell_type = cell.attrib.get("t")
            value = ""
            cell_value = cell.find(f"{{{main_namespace}}}v")
            if cell_value is not None and cell_value.text is not None:
                raw_value = cell_value.text
                if cell_type == "s":
                    try:
                        value = shared_strings[int(raw_value)]
                    except (IndexError, ValueError):
                        value = raw_value
                else:
                    value = raw_value

            if not value and cell_type == "inlineStr":
                inline_string = cell.find(f"{{{main_namespace}}}is")
                if inline_string is not None:
                    texts = [
                        text.text or ""
                        for text in inline_string.findall(f".//{{{main_namespace}}}t")
                    ]
                    value = "".join(texts)

            if not value:
                inline_string = cell.find(f"{{{main_namespace}}}is")
                if inline_string is not None:
                    texts = [
                        text.text or ""
                        for text in inline_string.findall(f".//{{{main_namespace}}}t")
                    ]
                    value = "".join(texts)

            rows.setdefault(row_number, {})[column_number] = value.strip()

        if not rows:
            return []

        max_row = max(rows.keys())
        max_column = max(max(row.keys()) for row in rows.values())
        output: list[list[str]] = []
        for row_number in range(1, max_row + 1):
            row = rows.get(row_number, {})
            output.append(
                [row.get(column_number, "") for column_number in range(1, max_column + 1)]
            )
        return output


def find_header_row_index(rows: list[list[str]], max_scan_rows: int = 30) -> int:
    scan_limit = min(len(rows), max_scan_rows)
    for index in range(scan_limit):
        row = rows[index]
        try:
            find_header_mapping(row)
            if any((cell or "").strip() for cell in row):
                return index
        except SpreadsheetError:
            continue
    raise SpreadsheetError(
        "Could not detect the header row in the spreadsheet "
        "(empty leading rows or unexpected headers)."
    )


def find_header_mapping(header_row: list[str]) -> dict[str, int | None]:
    normalized = [normalize_header(header) for header in header_row]

    def find_one(patterns: list[str]) -> int | None:
        for index, header in enumerate(normalized):
            for pattern in patterns:
                if re.search(pattern, header):
                    return index
        return None

    def previous_code(name_index: int) -> int | None:
        for index in range(name_index - 1, -1, -1):
            if normalized[index] == "codigo" or normalized[index].startswith("codigo"):
                return index
        return None

    department_name_index = find_one([r"^departamento$", r"nombre.*departamento"])
    district_name_index = find_one([r"^distritos?$", r"nombre.*distrito"])
    city_name_index = find_one(
        [
            r"^ciudades",
            r"^ciudad",
            r"ciudades.*localidades",
            r"localidades",
            r"ciudades / localidades",
        ]
    )
    neighborhood_name_index = find_one([r"^barrios$", r"^barrio$", r"nombre.*barrio"])

    if (
        department_name_index is not None
        and district_name_index is not None
        and city_name_index is not None
    ):
        mapping = {
            "dep_codigo": previous_code(department_name_index),
            "dep_nombre": department_name_index,
            "dis_codigo": previous_code(district_name_index),
            "dis_nombre": district_name_index,
            "ciu_codigo": previous_code(city_name_index),
            "ciu_nombre": city_name_index,
        }
    else:
        mapping = {
            "dep_codigo": find_one(
                [
                    r"codigo.*departamento",
                    r"cod.*departamento",
                    r"cod.*depto",
                    r"^dep.*codigo$",
                    r"^codigo dep",
                ]
            ),
            "dep_nombre": find_one(
                [r"^departamento$", r"nombre.*departamento", r"^dep(artamento)?$"]
            ),
            "dis_codigo": find_one(
                [
                    r"codigo.*distrito",
                    r"cod.*distrito",
                    r"^dis.*codigo$",
                    r"^codigo dis",
                ]
            ),
            "dis_nombre": find_one(
                [r"^distrito$", r"^distritos$", r"nombre.*distrito", r"^dist$"]
            ),
            "ciu_codigo": find_one(
                [
                    r"codigo.*ciudad",
                    r"codigo.*localidad",
                    r"cod.*ciudad",
                    r"cod.*localidad",
                    r"^ciu.*codigo$",
                    r"^codigo ciu",
                ]
            ),
            "ciu_nombre": find_one(
                [
                    r"^ciudad",
                    r"ciudad.*localidad",
                    r"localidad",
                    r"nombre.*ciudad",
                ]
            ),
        }

    if neighborhood_name_index is not None:
        mapping["bar_codigo"] = previous_code(neighborhood_name_index)
        mapping["bar_nombre"] = neighborhood_name_index

    required_keys = (
        "dep_codigo",
        "dep_nombre",
        "dis_codigo",
        "dis_nombre",
        "ciu_codigo",
        "ciu_nombre",
    )
    if neighborhood_name_index is not None:
        required_keys = required_keys + ("bar_codigo", "bar_nombre")

    missing = [key for key in required_keys if mapping.get(key) is None]
    if missing:
        raise SpreadsheetError(
            "Could not identify required columns in the spreadsheet. "
            f"Missing: {', '.join(missing)}. "
            "Check headers (Department code/Department/District code/District/"
            "City code/City/Neighborhood code/Neighborhood)."
        )

    return {key: int(value) if value is not None else None for key, value in mapping.items()}


def to_int(value: str, field_label: str) -> int:
    cleaned = (value or "").strip()
    if not cleaned:
        raise ValueError(f"{field_label} is empty")
    digits = re.sub(r"[^\d]", "", cleaned)
    if not digits:
        raise ValueError(f"{field_label} is invalid: {value!r}")
    return int(digits)


def extract_catalog_metadata(rows: list[list[str]], header_index: int) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for row in rows[:header_index]:
        cells = [(cell or "").strip() for cell in row if (cell or "").strip()]
        if len(cells) < 2:
            continue
        label = normalize_header(cells[0]).rstrip(":")
        if label == "fecha de actualizacion":
            metadata["catalog_date"] = cells[1]
        elif label == "fuente":
            metadata["source_url"] = cells[1]
    return metadata
