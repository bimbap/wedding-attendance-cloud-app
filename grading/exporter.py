"""Export grading results to JSON, CSV, and styled multi-sheet XLSX."""

import csv
import datetime
import json
import os
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

try:
    import openpyxl  # noqa: F401
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


PASS_THRESHOLD = 70


def build_participant_result(
    ctx: Any,
    participant: dict[str, str],
    pass_threshold: int = PASS_THRESHOLD,
) -> dict[str, Any]:
    """Build an aws-grading compatible result dictionary from a GradingContext."""
    checks = [c.to_dict() for c in ctx.checks]
    max_score = sum(c.points for c in ctx.checks)
    score = sum(c.points for c in ctx.checks if c.passed)
    pass_count = sum(1 for c in ctx.checks if c.passed)
    fail_count = len(ctx.checks) - pass_count
    percentage = int(round((score * 100) / max_score)) if max_score > 0 else 0
    is_passed = max_score > 0 and (score * 100 > max_score * pass_threshold)

    return {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "region": ctx.region,
        "pass_fail_system_enabled": True,
        "pass_threshold": pass_threshold,
        "status": "pass" if is_passed else "fail",
        "score": score,
        "max_score": max_score,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "percentage": percentage,
        "participant": {
            "name": participant.get("name") or "Participant",
            "institution": participant.get("institution", ""),
            "email": participant.get("email", ""),
            "account_id": ctx.account_id or participant.get("account_id", ""),
        },
        "checks": checks,
    }


def save_json(result: dict[str, Any], json_path: Path, append: bool = False) -> dict[str, Any]:
    """Write or update participant result into results.json (overwriting matching or previous run)."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"results": []}

    if append and json_path.exists():
        try:
            existing = json.loads(json_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict) and isinstance(existing.get("results"), list):
                payload["results"] = existing["results"]
        except (OSError, json.JSONDecodeError):
            pass

    if append and payload["results"]:
        new_name = str(result.get("participant", {}).get("name", "")).strip().lower()
        new_acc = str(result.get("participant", {}).get("account_id", "")).strip()
        replaced = False
        for idx, prev in enumerate(payload["results"]):
            prev_p = prev.get("participant", {}) if isinstance(prev, dict) else {}
            prev_name = str(prev_p.get("name", "")).strip().lower()
            prev_acc = str(prev_p.get("account_id", "")).strip()
            same_name = bool(new_name and prev_name == new_name)
            same_live_account = bool(new_acc and new_acc != "123456789012" and prev_acc == new_acc)
            if same_name or same_live_account:
                payload["results"][idx] = result
                replaced = True
                break
        if not replaced:
            payload["results"].append(result)
    else:
        payload["results"] = [result]

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def _sanitize_csv(value: Any) -> Any:
    if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{value}"
    return value


def save_csv(payload: dict[str, Any], csv_path: Path) -> None:
    """Export flattened grading results to CSV."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "participant_name",
        "institution",
        "account_id",
        "region",
        "category",
        "check",
        "points",
        "status",
        "detail",
        "score",
        "max_score",
        "percentage",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for r in payload.get("results", []):
            p = r.get("participant", {})
            for chk in r.get("checks", []):
                row = {
                    "participant_name": p.get("name", ""),
                    "institution": p.get("institution", ""),
                    "account_id": p.get("account_id", ""),
                    "region": r.get("region", ""),
                    "category": chk.get("category", ""),
                    "check": chk.get("name", ""),
                    "points": chk.get("points", 0),
                    "status": chk.get("status", "").upper(),
                    "detail": chk.get("detail", ""),
                    "score": r.get("score", 0),
                    "max_score": r.get("max_score", 0),
                    "percentage": r.get("percentage", 0),
                }
                writer.writerow({k: _sanitize_csv(v) for k, v in row.items()})


def _find_aws_grading_xlsx_converter() -> Path | None:
    """Locate sibling aws-grading/grading/export/convert_csv_to_xlsx.py if present."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "aws-grading" / "grading" / "export" / "convert_csv_to_xlsx.py"
        if candidate.is_file():
            return candidate
    return None


def _col_ref(row_idx: int, col_idx: int) -> str:
    letters = []
    idx = col_idx
    while idx >= 0:
        letters.append(chr((idx % 26) + 65))
        idx = idx // 26 - 1
    return "".join(reversed(letters)) + str(row_idx)


def _safe_sheet_name(raw_name: str, existing: set[str], fallback: str) -> str:
    cleaned = raw_name[:28]
    for ch in "/\\*?[]:'":
        cleaned = cleaned.replace(ch, "")
    name = cleaned.strip() or fallback
    if name in existing:
        name = f"{name[:24]}_{len(existing) + 1}"
    existing.add(name)
    return name


def _build_sheet_xml(
    rows: list[list[tuple[Any, int]]],
    col_widths: list[int],
    add_str,
    merges: list[str] | None = None,
    row_heights: dict[int, int] | None = None,
) -> str:
    cols_xml = "".join(
        f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>'
        for i, w in enumerate(col_widths, start=1)
    )
    heights = row_heights or {}
    row_xml_parts = []
    for r_idx, row in enumerate(rows, start=1):
        cells = []
        for c_idx, (val, style_id) in enumerate(row):
            ref = _col_ref(r_idx, c_idx)
            if val is None or val == "":
                cells.append(f'<c r="{ref}" s="{style_id}"/>')
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                cells.append(f'<c r="{ref}" s="{style_id}"><v>{val}</v></c>')
            else:
                s_idx = add_str(str(val))
                cells.append(f'<c r="{ref}" t="s" s="{style_id}"><v>{s_idx}</v></c>')
        ht_attr = f' ht="{heights[r_idx]}" customHeight="1"' if r_idx in heights else ""
        row_xml_parts.append(f'<row r="{r_idx}"{ht_attr}>{"".join(cells)}</row>')

    merge_xml = ""
    if merges:
        merge_tags = "".join(f'<mergeCell ref="{ref}"/>' for ref in merges)
        merge_xml = f'<mergeCells count="{len(merges)}">{merge_tags}</mergeCells>'

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<cols>{cols_xml}</cols>"
        f"<sheetData>{''.join(row_xml_parts)}</sheetData>"
        f"{merge_xml}"
        "</worksheet>"
    )


def _write_stdlib_xlsx(payload: dict[str, Any], xlsx_path: Path) -> str:
    """Zero-dependency styled OOXML XLSX generator when openpyxl is absent."""
    results = sorted(payload.get("results", []), key=lambda r: r.get("percentage", 0), reverse=True)
    shared_strings: list[str] = []
    str_index: dict[str, int] = {}

    def add_str(value: str) -> int:
        if value not in str_index:
            str_index[value] = len(shared_strings)
            shared_strings.append(value)
        return str_index[value]

    # Style indices in styles.xml:
    # 0: normal, 1: banner (dark fill, white bold), 2: table header (slate fill, white bold),
    # 3: pass (green fill, dark green bold), 4: fail (red fill, dark red bold), 5: bold
    sheets: list[tuple[str, str]] = []
    used_names: set[str] = set()

    if len(results) > 1:
        rank_rows: list[list[tuple[Any, int]]] = [
            [("HASIL PENILAIAN - SERVERLESS CLOUD ARCHITECTURE", 1), ("", 1), ("", 1), ("", 1), ("", 1), ("", 1), ("", 1)],
            [("Rank", 2), ("Nama Peserta", 2), ("Instansi", 2), ("Score", 2), ("Max", 2), ("Percentage", 2), ("Status", 2)],
        ]
        for idx, res in enumerate(results, start=1):
            p = res.get("participant", {})
            st = res.get("status", "fail").upper()
            st_style = 3 if st == "PASS" else 4
            rank_rows.append([
                (idx, 5),
                (p.get("name") or "Participant", 0),
                (p.get("institution") or "-", 0),
                (res.get("score", 0), 0),
                (res.get("max_score", 0), 0),
                (f"{res.get('percentage', 0)}%", 5),
                (st, st_style),
            ])
        sheets.append((
            _safe_sheet_name("Ranking", used_names, "Ranking"),
            _build_sheet_xml(rank_rows, [8, 32, 28, 10, 10, 14, 12], add_str, merges=["A1:G1"], row_heights={1: 28, 2: 22}),
        ))

    for idx, res in enumerate(results, start=1):
        p = res.get("participant", {})
        p_name = p.get("name") or f"Participant {idx}"
        p_inst = p.get("institution") or "-"
        p_acc = p.get("account_id") or "-"
        st = res.get("status", "fail").upper()
        detail_rows: list[list[tuple[Any, int]]] = [
            [(f"Detail Penilaian - {p_name} [{st}]", 1), ("", 1), ("", 1), ("", 1), ("", 1)],
            [(f"Instansi: {p_inst} | Account: {p_acc} | Score: {res.get('score', 0)}/{res.get('max_score', 0)} ({res.get('percentage', 0)}%)", 5), ("", 5), ("", 5), ("", 5), ("", 5)],
            [("Kategori", 2), ("Check", 2), ("Pts", 2), ("Status", 2), ("Detail", 2)],
        ]
        for chk in res.get("checks", []):
            cst = chk.get("status", "fail").upper()
            cst_style = 3 if cst == "PASS" else 4
            detail_rows.append([
                (chk.get("category", ""), 5),
                (chk.get("name", ""), 0),
                (chk.get("points", 0), 0),
                (cst, cst_style),
                (chk.get("detail", ""), 0),
            ])
        sheets.append((
            _safe_sheet_name(p_name, used_names, f"Participant_{idx}"),
            _build_sheet_xml(detail_rows, [18, 48, 8, 12, 66], add_str, merges=["A1:E1", "A2:E2"], row_heights={1: 28, 2: 22, 3: 22}),
        ))

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="5">'
        '<font><sz val="11"/><name val="Calibri"/></font>'
        '<font><b/><sz val="12"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><color rgb="FF15803D"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><color rgb="FFB91C1C"/><name val="Calibri"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/></font>'
        '</fonts>'
        '<fills count="6">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF1E293B"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FF334155"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFDCFCE7"/></patternFill></fill>'
        '<fill><patternFill patternType="solid"><fgColor rgb="FFFEE2E2"/></patternFill></fill>'
        '</fills>'
        '<borders count="2">'
        '<border/>'
        '<border><left style="thin"><color rgb="FFE2E8F0"/></left><right style="thin"><color rgb="FFE2E8F0"/></right>'
        '<top style="thin"><color rgb="FFE2E8F0"/></top><bottom style="thin"><color rgb="FFE2E8F0"/></bottom></border>'
        '</borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="6">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="0" applyFont="1" applyFill="1"/>'
        '<xf numFmtId="0" fontId="1" fillId="3" borderId="1" applyFont="1" applyFill="1" applyBorder="1"/>'
        '<xf numFmtId="0" fontId="2" fillId="4" borderId="1" applyFont="1" applyFill="1" applyBorder="1"/>'
        '<xf numFmtId="0" fontId="3" fillId="5" borderId="1" applyFont="1" applyFill="1" applyBorder="1"/>'
        '<xf numFmtId="0" fontId="4" fillId="0" borderId="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>'
        '</cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )

    sst_items = "".join(f"<si><t>{escape(s)}</t></si>" for s in shared_strings)
    shared_strings_xml = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">'
        f"{sst_items}</sst>"
    )

    sheet_tags = "".join(
        f'<sheet name="{escape(name)}" sheetId="{i}" r:id="rId{i}"/>'
        for i, (name, _) in enumerate(sheets, start=1)
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheet_tags}</sheets></workbook>"
    )

    wb_rels = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, len(sheets) + 1)
    ) + f'<Relationship Id="rId{len(sheets)+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    wb_rels += f'<Relationship Id="rId{len(sheets)+2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{wb_rels}</Relationships>"
    )

    overrides = "".join(
        f'<Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        for i in range(1, len(sheets) + 1)
    )
    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        f"{overrides}"
        '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        '</Types>'
    )
    root_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )

    target_path = xlsx_path
    try:
        with zipfile.ZipFile(target_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types_xml)
            zf.writestr("_rels/.rels", root_rels_xml)
            zf.writestr("xl/workbook.xml", workbook_xml)
            zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
            zf.writestr("xl/styles.xml", styles_xml)
            zf.writestr("xl/sharedStrings.xml", shared_strings_xml)
            for i, (_, xml_body) in enumerate(sheets, start=1):
                zf.writestr(f"xl/worksheets/sheet{i}.xml", xml_body)
    except PermissionError:
        counter = 1
        while True:
            fallback = xlsx_path.with_stem(f"{xlsx_path.stem}_{counter}")
            try:
                with zipfile.ZipFile(fallback, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.writestr("[Content_Types].xml", content_types_xml)
                    zf.writestr("_rels/.rels", root_rels_xml)
                    zf.writestr("xl/workbook.xml", workbook_xml)
                    zf.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
                    zf.writestr("xl/styles.xml", styles_xml)
                    zf.writestr("xl/sharedStrings.xml", shared_strings_xml)
                    for i, (_, xml_body) in enumerate(sheets, start=1):
                        zf.writestr(f"xl/worksheets/sheet{i}.xml", xml_body)
                print(f"[NOTE] '{xlsx_path}' is open/locked. Saved to '{fallback}' instead.", file=sys.stderr)
                return str(fallback)
            except PermissionError:
                counter += 1

    return str(target_path)


def save_xlsx(payload: dict[str, Any], json_path: Path, xlsx_path: Path) -> tuple[str, str]:
    """Export grading results to XLSX using aws-grading's openpyxl formatter or stdlib fallback."""
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    converter = _find_aws_grading_xlsx_converter()

    if OPENPYXL_AVAILABLE and converter is not None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("aws_grading_xlsx", str(converter))
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            os.environ["PASS_FAIL_SYSTEM_ENABLED"] = "true"
            os.environ["PASS_THRESHOLD"] = str(PASS_THRESHOLD)
            spec.loader.exec_module(mod)
            saved = mod.create_workbook_from_json(payload, str(xlsx_path))
            return str(saved), "openpyxl (aws-grading)"

    saved = _write_stdlib_xlsx(payload, xlsx_path)
    return saved, "stdlib-ooxml"
