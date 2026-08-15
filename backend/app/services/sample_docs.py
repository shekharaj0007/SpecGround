"""Generate fictional engineering PDFs for the demo.

These are original training documents, not copies of ASME/ISO/ASTM.
Labeled clearly so they can be used in a public portfolio.
"""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

BRASS = colors.HexColor("#b45309")
STEEL = colors.HexColor("#1e293b")
RULE = colors.HexColor("#cbd5e1")
HEADER_BG = colors.HexColor("#0f172a")
ROW_ALT = colors.HexColor("#f8fafc")


def _styles():
    base = getSampleStyleSheet()
    styles = {
        "banner": ParagraphStyle(
            "banner",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=9,
            textColor=BRASS,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=18,
            textColor=STEEL,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "sub": ParagraphStyle(
            "sub",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475569"),
            spaceAfter=16,
        ),
        "h": ParagraphStyle(
            "h",
            parent=base["Heading1"],
            fontName="Times-Bold",
            fontSize=12,
            textColor=STEEL,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            leading=14,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "eq": ParagraphStyle(
            "eq",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=11,
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=6,
        ),
        "note": ParagraphStyle(
            "note",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=8,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER,
            spaceBefore=18,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
        ),
    }
    return styles


def _table(data: list[list[str]], col_widths=None) -> Table:
    s = _styles()["cell"]
    wrapped = [[Paragraph(str(c), s) for c in row] for row in data]
    t = Table(wrapped, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, RULE),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ROW_ALT]),
            ]
        )
    )
    return t


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(BRASS)
    canvas.setLineWidth(1.2)
    canvas.line(0.75 * inch, letter[1] - 0.45 * inch, letter[0] - 0.75 * inch, letter[1] - 0.45 * inch)
    canvas.setFont("Times-Italic", 8)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(0.75 * inch, 0.45 * inch, "SpecGround sample — fictional training document, not an official code")
    canvas.drawRightString(letter[0] - 0.75 * inch, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


def write_piping_code(path: Path) -> None:
    s = _styles()
    story = [
        Paragraph("SPECGROUND TRAINING LIBRARY  ·  SG-PIPING-2024", s["banner"]),
        Paragraph("Process Piping Design Code — Training Excerpt", s["title"]),
        Paragraph(
            "Fictional document for software demonstration. Not an ASME, ISO, or API standard. "
            "Do not use for design.",
            s["sub"],
        ),
        Paragraph("1 Scope", s["h"]),
        Paragraph(
            "This code applies to process piping in chemical, petroleum, and related industries "
            "for fluids that are not Category M. It covers design pressure, pressure design of "
            "straight pipe, and listed material allowable stresses for carbon steel. Piping "
            "systems designed to this excerpt shall be identified as SG-PIPING-2024.",
            s["body"],
        ),
        Paragraph("2 Definitions", s["h"]),
        Paragraph(
            "2.1 Design pressure. The pressure used in the design of a piping component, "
            "which shall not be less than the most severe coincident pressure expected during "
            "normal operation, including hydrostatic head.",
            s["body"],
        ),
        Paragraph(
            "2.2 Design temperature. The metal temperature representing the most severe "
            "coincident condition of pressure and temperature. For uninsulated pipe, the "
            "metal temperature shall be taken as the fluid temperature unless a documented "
            "heat-transfer analysis justifies a lower value.",
            s["body"],
        ),
        Paragraph(
            "2.3 MAWP. Maximum allowable working pressure of a component at the designated "
            "temperature, computed from the pressure-design equations of Section 4 using the "
            "allowable stress from Table 4.1-1.",
            s["body"],
        ),
        Paragraph("3 Design Conditions", s["h"]),
        Paragraph(
            "3.1 Design pressure shall not be less than the most severe coincident pressure "
            "expected during normal operation. The design pressure for Category D fluid service "
            "shall be at least 150 psi (1.03 MPa) at the design temperature, unless a lower "
            "value is justified by a documented process-safety review.",
            s["body"],
        ),
        Paragraph(
            "3.2 A corrosion allowance of 0.063 in (1.6 mm) shall be added to the pressure "
            "design thickness for carbon steel in water and steam service unless the owner "
            "specifies otherwise. Threaded joints are not permitted above 250 psi (1.72 MPa) "
            "in flammable fluid service.",
            s["body"],
        ),
        PageBreak(),
        Paragraph("4 Pressure Design of Components", s["h"]),
        Paragraph("4.1 Straight Pipe", s["h"]),
        Paragraph("4.1.1 Internal Pressure", s["h"]),
        Paragraph(
            "The minimum required wall thickness t for straight pipe under internal pressure is:",
            s["body"],
        ),
        Paragraph("t = (P × D) / (2 × (S × E × W + P × Y)) + c", s["eq"]),
        Paragraph(
            "where P is design pressure (psi), D is outside diameter (in), S is allowable "
            "stress from Table 4.1-1 (psi), E is weld joint quality factor (1.00 for seamless, "
            "0.80 for electric-fusion-welded without radiography), W is weld joint strength "
            "reduction factor (1.00 at or below 700 °F / 371 °C), Y is the temperature "
            "coefficient (0.4 for ferritic steels at or below 900 °F), and c is corrosion "
            "and mechanical allowances (in).",
            s["body"],
        ),
        Paragraph(
            "4.1.2 The mill under-tolerance of 12.5% for A106 seamless pipe shall be accounted "
            "for by dividing the ordered wall by 0.875 when checking against t.",
            s["body"],
        ),
        Paragraph("Table 4.1-1 Allowable Stresses for Carbon Steel (A106 Grade B, seamless)", s["h"]),
        _table(
            [
                ["Metal temperature °F", "Metal temperature °C", "Allowable stress ksi", "Allowable stress MPa"],
                ["100", "38", "20.0", "137.9"],
                ["200", "93", "20.0", "137.9"],
                ["300", "149", "20.0", "137.9"],
                ["400", "204", "20.0", "137.9"],
                ["500", "260", "18.9", "130.3"],
                ["600", "316", "17.3", "119.3"],
                ["700", "371", "16.5", "113.8"],
                ["800", "427", "10.8", "74.5"],
            ],
            col_widths=[1.6 * inch, 1.6 * inch, 1.6 * inch, 1.6 * inch],
        ),
        Spacer(1, 10),
        Paragraph(
            "Values above 700 °F are shown for information only. Design of A106 Grade B "
            "to this excerpt is not permitted above 800 °F (427 °C).",
            s["body"],
        ),
        Paragraph("4.2 External Pressure", s["h"]),
        Paragraph(
            "Straight pipe under external pressure shall be checked per the procedure in "
            "Section 4.2. For NPS 6 Schedule 40 A106 Grade B, the maximum allowable external "
            "pressure at 300 °F is 430 psi (2.96 MPa) for an unsupported length of 10 ft "
            "(3.05 m). Longer unsupported spans require stiffening rings.",
            s["body"],
        ),
        Paragraph("5 Flexibility and Support", s["h"]),
        Paragraph(
            "5.1 Piping shall be designed to absorb thermal expansion. The allowable "
            "displacement stress range SA is 1.25 Sc + 0.25 Sh, where Sc and Sh are the "
            "allowable stresses at cold and hot temperatures from Table 4.1-1.",
            s["body"],
        ),
        Paragraph(
            "5.2 Support spacing for NPS 4 water-filled carbon steel pipe shall not exceed "
            "14 ft (4.3 m) between supports unless a pipe-stress analysis demonstrates "
            "adequacy. Valves heavier than 50 lb (22.7 kg) shall be independently supported.",
            s["body"],
        ),
        Paragraph(
            "This excerpt ends. It is a SpecGround sample used to demonstrate grounded "
            "retrieval, table Q&A, and citation highlighting.",
            s["note"],
        ),
    ]
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        title="SG-PIPING-2024 Process Piping Design Code — Training Excerpt",
        author="SpecGround",
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def write_pump_datasheet(path: Path) -> None:
    s = _styles()
    story = [
        Paragraph("SPECGROUND TRAINING LIBRARY  ·  DATASHEET CP-450", s["banner"]),
        Paragraph("Centrifugal Pump Datasheet — Model CP-450", s["title"]),
        Paragraph(
            "End-suction centrifugal pump for cooling-water and light-hydrocarbon service. "
            "Fictional OEM datasheet for software demonstration.",
            s["sub"],
        ),
        Paragraph("1 Identification", s["h"]),
        Paragraph(
            "Manufacturer: Northforge Rotating Equipment. Model CP-450. Impeller diameter "
            "11.0 in (279 mm) as shipped. Rotation CW viewed from coupling end. Driver "
            "interface is a 56 frame C-face adapter; the pump is not self-priming.",
            s["body"],
        ),
        Paragraph("2 Rated Performance", s["h"]),
        Paragraph(
            "Rated operating point is 450 gpm (102 m³/h) at 180 ft (54.9 m) total dynamic "
            "head, 1750 rpm, water at 68 °F (20 °C), specific gravity 1.00. Best efficiency "
            "point (BEP) is 470 gpm at 175 ft. Minimum continuous stable flow is 90 gpm "
            "(20.4 m³/h). Shutoff head is 210 ft (64.0 m).",
            s["body"],
        ),
        Paragraph("Table 2-1 Performance at 1750 rpm, water 68 °F", s["h"]),
        _table(
            [
                ["Flow gpm", "Flow m³/h", "Head ft", "Head m", "Efficiency %", "NPSHr ft", "Power bhp"],
                ["0", "0", "210", "64.0", "—", "—", "18.5"],
                ["200", "45.4", "198", "60.4", "62", "6.5", "22.1"],
                ["350", "79.5", "188", "57.3", "74", "8.2", "26.8"],
                ["450", "102.2", "180", "54.9", "78", "9.5", "29.4"],
                ["470", "106.7", "175", "53.3", "79", "10.0", "29.8"],
                ["550", "124.9", "158", "48.2", "75", "13.8", "33.1"],
            ],
            col_widths=[1.05 * inch] * 7,
        ),
        Spacer(1, 12),
        Paragraph("3 Materials and Limits", s["h"]),
        Paragraph(
            "Casing is ASTM A216 WCB carbon steel. Impeller is ASTM A48 Class 30 cast iron. "
            "Shaft is AISI 4140. Mechanical seal is a Type 21 carbon/ceramic, EPDM elastomer, "
            "rated to 250 °F (121 °C) and 150 psig (1.03 MPa). Maximum allowable working "
            "pressure of the casing is 175 psig (1.21 MPa) at 250 °F. Maximum pumped-fluid "
            "temperature is 250 °F (121 °C) with the standard seal; 350 °F (177 °C) requires "
            "the optional bellows seal and oil-mist lubrication.",
            s["body"],
        ),
        Paragraph("4 Nozzles and Connections", s["h"]),
        Paragraph(
            "Suction nozzle is 4 in 150 lb RF flange (NPS 4). Discharge nozzle is 3 in "
            "150 lb RF flange (NPS 3). Flange rating shall not be used above the casing MAWP "
            "of 175 psig. Suction piping velocity should not exceed 8 ft/s (2.4 m/s).",
            s["body"],
        ),
        Paragraph("5 Lubrication and Utilities", s["h"]),
        Paragraph(
            "Bearings are grease-lubricated; relubricate every 2000 operating hours with "
            "lithium-complex grease NLGI 2. Seal flush is Plan 11 from discharge through a "
            "0.125 in orifice. Cooling water is not required below 180 °F pumped fluid.",
            s["body"],
        ),
        Paragraph("Fictional OEM datasheet. Not for procurement or installation.", s["note"]),
    ]
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        title="CP-450 Centrifugal Pump Datasheet",
        author="SpecGround",
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


def write_material_spec(path: Path) -> None:
    s = _styles()
    story = [
        Paragraph("SPECGROUND TRAINING LIBRARY  ·  MS-A106-B", s["banner"]),
        Paragraph("Carbon Steel Pipe — Material Spec MS-A106 (Sample)", s["title"]),
        Paragraph(
            "Seamless carbon steel pipe for high-temperature service. Fictional material "
            "specification aligned with common industry practice for demo use only.",
            s["sub"],
        ),
        Paragraph("1 Scope", s["h"]),
        Paragraph(
            "This specification covers seamless carbon steel pipe in Grade B for NPS 1/8 "
            "through NPS 26, wall thicknesses through Schedule 160. Pipe is intended for "
            "bending, flanging, and similar forming operations, and for welding. Grade A "
            "and Grade C are out of scope of this sample.",
            s["body"],
        ),
        Paragraph("2 Chemical Composition — Grade B", s["h"]),
        Paragraph(
            "Heat analysis shall conform to Table 2-1. Product analysis tolerances are "
            "permitted as listed. Carbon equivalent CE shall not exceed 0.43 for pipe that "
            "will be welded without PWHT, where CE = C + Mn/6 + (Cr+Mo+V)/5 + (Ni+Cu)/15.",
            s["body"],
        ),
        Paragraph("Table 2-1 Chemical composition, heat analysis, Grade B (wt %)", s["h"]),
        _table(
            [
                ["Element", "Minimum", "Maximum"],
                ["Carbon (C)", "—", "0.30"],
                ["Manganese (Mn)", "0.29", "1.06"],
                ["Phosphorus (P)", "—", "0.035"],
                ["Sulfur (S)", "—", "0.035"],
                ["Silicon (Si)", "0.10", "0.35"],
                ["Chromium (Cr)", "—", "0.40"],
                ["Copper (Cu)", "—", "0.40"],
                ["Molybdenum (Mo)", "—", "0.15"],
                ["Nickel (Ni)", "—", "0.40"],
                ["Vanadium (V)", "—", "0.08"],
            ],
            col_widths=[2.4 * inch, 2.0 * inch, 2.0 * inch],
        ),
        Spacer(1, 12),
        Paragraph("3 Mechanical Properties", s["h"]),
        Paragraph(
            "Tensile strength shall be 60 ksi (415 MPa) minimum. Yield strength shall be "
            "35 ksi (240 MPa) minimum. Elongation in 2 in (50 mm) shall be 30% minimum for "
            "longitudinal specimens. Hardness shall not exceed 197 HBW.",
            s["body"],
        ),
        Paragraph("Table 3-1 Mechanical properties, Grade B", s["h"]),
        _table(
            [
                ["Property", "US customary", "SI"],
                ["Tensile strength, min", "60 ksi", "415 MPa"],
                ["Yield strength, min", "35 ksi", "240 MPa"],
                ["Elongation in 2 in, min", "30%", "30%"],
                ["Hardness, max", "197 HBW", "197 HBW"],
            ],
            col_widths=[2.4 * inch, 2.0 * inch, 2.0 * inch],
        ),
        Spacer(1, 12),
        Paragraph("4 Dimensions and Hydrotest", s["h"]),
        Paragraph(
            "Pipe shall be furnished to ASME B36.10M dimensions. NPS 6 Schedule 40 has an "
            "outside diameter of 6.625 in (168.3 mm) and a nominal wall of 0.280 in (7.11 mm). "
            "Each length shall be hydrostatically tested at 2500 psi (17.2 MPa) or the "
            "pressure computed from P = 2St/D with S = 60% of specified minimum yield, "
            "whichever is lower. Nondestructive electric testing may replace hydrotest "
            "when specified by the purchaser.",
            s["body"],
        ),
        Paragraph(
            "4.1 Marking. Each length shall be marked MS-A106-B, heat number, NPS, schedule, "
            "and the letters SMLS. Pipe furnished to this spec is compatible with the "
            "allowable stresses listed for A106 Grade B in SG-PIPING-2024 Table 4.1-1.",
            s["body"],
        ),
        Paragraph("Fictional material spec. Not for purchasing or fabrication.", s["note"]),
    ]
    doc = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        title="MS-A106 Carbon Steel Pipe Material Spec (Sample)",
        author="SpecGround",
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
    )
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)


SAMPLES = [
    ("SG-PIPING-2024_Process_Piping_Training_Excerpt.pdf", write_piping_code, "standard"),
    ("CP-450_Centrifugal_Pump_Datasheet.pdf", write_pump_datasheet, "datasheet"),
    ("MS-A106_Carbon_Steel_Pipe_Material_Spec.pdf", write_material_spec, "material_spec"),
]


def generate_all(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for filename, writer, _doc_type in SAMPLES:
        path = output_dir / filename
        writer(path)
        paths.append(path)
    return paths
