from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

XLSX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _xml(value: Any) -> str:
    return escape(str(value), {'"': "&quot;", "'": "&apos;"})


def _col_name(index: int) -> str:
    name = ""
    value = max(1, index)
    while value:
        value, remainder = divmod(value - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _cell(ref: str, value: Any) -> str:
    if isinstance(value, bool):
        return f'<c r="{ref}" t="b"><v>{1 if value else 0}</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}"><v>{value}</v></c>'
    if isinstance(value, str) and value.startswith("="):
        return f'<c r="{ref}"><f>{_xml(value[1:])}</f></c>'
    return f'<c r="{ref}" t="inlineStr"><is><t>{_xml(value)}</t></is></c>'


def _worksheet_xml(rows: list[list[Any]], *, freeze_header: bool = True, autofilter: bool = True) -> str:
    safe_rows = rows or [["empty"]]
    max_cols = max((len(row) for row in safe_rows), default=1)
    max_rows = len(safe_rows)
    rendered_rows = []
    for row_index, row in enumerate(safe_rows, start=1):
        cells = "".join(_cell(f"{_col_name(column_index)}{row_index}", value) for column_index, value in enumerate(row, start=1))
        rendered_rows.append(f'<row r="{row_index}">{cells}</row>')
    dimension = f"A1:{_col_name(max_cols)}{max_rows}"
    freeze = """
  <sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>""" if freeze_header and max_rows > 1 else "<sheetViews><sheetView workbookViewId=\"0\"/></sheetViews>"
    filter_xml = f'<autoFilter ref="{dimension}"/>' if autofilter and max_rows > 1 and max_cols > 1 else ""
    cols = "".join(f'<col min="{idx}" max="{idx}" width="18" customWidth="1"/>' for idx in range(1, max_cols + 1))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <dimension ref="{dimension}"/>
  {freeze}
  <sheetFormatPr defaultRowHeight="18"/>
  <cols>{cols}</cols>
  <sheetData>{''.join(rendered_rows)}</sheetData>
  {filter_xml}
</worksheet>
'''


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets = "".join(f'<sheet name="{_xml(name[:31] or f"Sheet {index}")}" sheetId="{index}" r:id="rId{index}"/>' for index, name in enumerate(sheet_names, start=1))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <workbookPr date1904="0"/>
  <sheets>{sheets}</sheets>
  <calcPr calcId="191029" fullCalcOnLoad="1"/>
</workbook>
'''


def _workbook_rels_xml(sheet_count: int) -> str:
    rels = "".join(f'<Relationship Id="rId{index}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{index}.xml"/>' for index in range(1, sheet_count + 1))
    rels += f'<Relationship Id="rId{sheet_count + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>
'''


def _root_rels_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
'''


def _content_types_xml(sheet_count: int) -> str:
    sheets = "".join(f'<Override PartName="/xl/worksheets/sheet{index}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' for index in range(1, sheet_count + 1))
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  {sheets}
</Types>
'''


def _styles_xml() -> str:
    return '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="2"><font><sz val="11"/><name val="Aptos"/></font><font><b/><sz val="11"/><name val="Aptos"/></font></fonts>
  <fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>
  <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="2"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyFont="1"/></cellXfs>
  <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>
'''


def _core_xml(title: str) -> str:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{_xml(title)}</dc:title>
  <dc:creator>Nanus Spreadsheet Studio</dc:creator>
  <cp:lastModifiedBy>Nanus Spreadsheet Studio</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>
</cp:coreProperties>
'''


def _app_xml(sheet_count: int) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>Nanus</Application>
  <Worksheets>{sheet_count}</Worksheets>
</Properties>
'''


def build_xlsx_bytes(title: str, sheets: list[dict[str, Any]]) -> bytes:
    safe_sheets = [sheet for sheet in sheets if isinstance(sheet.get("rows"), list)] or [{"name": "README", "rows": [["Nanus Workbook"], ["No data rows supplied"]]}]
    buffer = BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", _content_types_xml(len(safe_sheets)))
        package.writestr("_rels/.rels", _root_rels_xml())
        package.writestr("docProps/core.xml", _core_xml(title))
        package.writestr("docProps/app.xml", _app_xml(len(safe_sheets)))
        package.writestr("xl/workbook.xml", _workbook_xml([str(sheet.get("name") or f"Sheet {index}") for index, sheet in enumerate(safe_sheets, start=1)]))
        package.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(len(safe_sheets)))
        package.writestr("xl/styles.xml", _styles_xml())
        for index, sheet in enumerate(safe_sheets, start=1):
            package.writestr(f"xl/worksheets/sheet{index}.xml", _worksheet_xml(sheet.get("rows", [])))
    return buffer.getvalue()
