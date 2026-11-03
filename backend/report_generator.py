"""PDF calculation note generator for CotaStack using ReportLab.

Produces clean, standardized A4 PDF calculation sheets for mechanical engineering
design reviews and quality records.
"""

import io
from datetime import date
import html
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

from backend.models import Item, ChainResult
from backend.calculator import ChainCalculator
from backend.multi_chain import MultiChainProject, AssemblyChain
from reportlab.graphics.shapes import Drawing, Line, String, Polygon, Rect, Group


def generate_pdf_report(
    items: list[Item],
    result: ChainResult,
    project_metadata: dict[str, Any] | None = None,
    thermal_summary: dict[str, Any] | None = None,
    monte_carlo_summary: dict[str, Any] | None = None,
) -> bytes:
    """Generate professional A4 PDF calculation report as raw bytes.

    Args:
        items: List of chain links.
        result: Calculated ChainResult (WC, RSS, Compliance).
        project_metadata: Dict with title, author, revision, date.
        thermal_summary: Optional thermal expansion metrics.
        monte_carlo_summary: Optional Monte Carlo PPM and capability metrics.

    Returns:
        bytes: Raw PDF content ready for file download or archiving.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#0284c7")
    dark_color = colors.HexColor("#0f172a")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=primary_color,
    )
    h2_style = ParagraphStyle(
        "SectionH2",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=dark_color,
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=dark_color,
    )
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#475569"),
    )
    meta_val = ParagraphStyle(
        "MetaVal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=dark_color,
    )
    cell_header = ParagraphStyle(
        "CellHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=1,
    )
    cell_body = ParagraphStyle(
        "CellBody",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=dark_color,
        alignment=1,
    )

    # Security: escape user-controlled text inputs to prevent ReportLab XML/HTML markup injection
    meta = project_metadata or {}
    proj_title = html.escape(str(meta.get("title", "Chaîne de cotes 1D — Note de calcul")))
    author = html.escape(str(meta.get("author", "Bureau d'Études Mécanique")))
    revision = html.escape(str(meta.get("revision", "A")))
    today_str = html.escape(str(meta.get("date", str(date.today()))))

    elements = []

    # 1. Header Title
    elements.append(Paragraph(f"📐 CotaStack — {proj_title}", title_style))
    elements.append(Paragraph("Note de calcul de tolérancement 1D — Conforme pratiques ISO GPS", body_style))
    elements.append(Spacer(1, 8 * mm))

    # 2. Cartouche Table
    cartouche_data = [
        [
            Paragraph("Projet :", meta_label),
            Paragraph(f"<b>{proj_title}</b>", meta_val),
            Paragraph("Indice Rév. :", meta_label),
            Paragraph(f"<b>{revision}</b>", meta_val),
        ],
        [
            Paragraph("Auteur / BE :", meta_label),
            Paragraph(author, meta_val),
            Paragraph("Date :", meta_label),
            Paragraph(today_str, meta_val),
        ],
    ]
    cartouche_table = Table(cartouche_data, colWidths=[25 * mm, 65 * mm, 25 * mm, 65 * mm])
    cartouche_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(cartouche_table)
    elements.append(Spacer(1, 6 * mm))

    # 3. Table of Links
    elements.append(Paragraph("1. Tableau des maillons dimensionnels", h2_style))

    table_rows = [
        [
            Paragraph("Repère", cell_header),
            Paragraph("Sens", cell_header),
            Paragraph("Nominal (mm)", cell_header),
            Paragraph("EI (mm)", cell_header),
            Paragraph("ES (mm)", cell_header),
            Paragraph("IT (mm)", cell_header),
            Paragraph("Cote moy. (mm)", cell_header),
            Paragraph("Matériau", cell_header),
        ]
    ]

    for item in items:
        sign_str = "+" if item.orientation > 0 else "-"
        mat_str = item.material or "Acier"
        # Security: escape item names and materials to prevent XML parser errors or markup injection
        safe_name = html.escape(str(item.name))
        safe_mat = html.escape(str(mat_str.split()[0]))
        table_rows.append([
            Paragraph(safe_name, cell_body),
            Paragraph(sign_str, cell_body),
            Paragraph(f"{item.nominal:.4f}", cell_body),
            Paragraph(f"{item.ei:+.4f}", cell_body),
            Paragraph(f"{item.es:+.4f}", cell_body),
            Paragraph(f"{item.IT:.4f}", cell_body),
            Paragraph(f"{item.L_moy:.4f}", cell_body),
            Paragraph(safe_mat, cell_body),
        ])

    items_table = Table(table_rows, colWidths=[36 * mm, 12 * mm, 22 * mm, 18 * mm, 18 * mm, 18 * mm, 24 * mm, 32 * mm])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), primary_color),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 6 * mm))

    # 4. Results Section (3 Distinct Compliance Criteria)
    elements.append(Paragraph("2. Bilan des résultats de calcul et conformité (3 critères)", h2_style))

    it_wc = sum(it.IT for it in items)
    it_rss = (sum(it.IT ** 2 for it in items)) ** 0.5

    c_info = result.compliance
    wc_comp_str = "CONFORME (GO)" if c_info.get("wc_compliant", True) else "NON CONFORME (NO-GO)"
    rss_comp_str = "CONFORME (GO)" if c_info.get("rss_compliant", True) else "NON CONFORME (NO-GO)"

    results_data = [
        [
            Paragraph("Méthode", cell_header),
            Paragraph("Jeu Min (mm)", cell_header),
            Paragraph("Jeu Moyen (mm)", cell_header),
            Paragraph("Jeu Max (mm)", cell_header),
            Paragraph("IT Total (mm)", cell_header),
            Paragraph("Verdict Global", cell_header),
        ],
        [
            Paragraph("<b>Pire des Cas (WC)</b>", cell_body),
            Paragraph(f"{result.worst_case_minus:.4f}", cell_body),
            Paragraph(f"{result.mean:.4f}", cell_body),
            Paragraph(f"{result.worst_case_plus:.4f}", cell_body),
            Paragraph(f"{it_wc:.4f}", cell_body),
            Paragraph(f"<b>{wc_comp_str}</b>", cell_body),
        ],
        [
            Paragraph("<b>Statistique (RSS 3σ)</b>", cell_body),
            Paragraph(f"{result.rss_minus:.4f}", cell_body),
            Paragraph(f"{result.mean:.4f}", cell_body),
            Paragraph(f"{result.rss_plus:.4f}", cell_body),
            Paragraph(f"{it_rss:.4f}", cell_body),
            Paragraph(f"<b>{rss_comp_str}</b>", cell_body),
        ],
    ]

    res_table = Table(results_data, colWidths=[40 * mm, 26 * mm, 28 * mm, 26 * mm, 26 * mm, 34 * mm])
    res_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
    ]))
    elements.append(res_table)
    elements.append(Spacer(1, 3 * mm))

    # Detailed 3-Criteria Compliance Table if targets are configured
    if result.target_min is not None or result.target_max is not None:
        t_min_str = f"{result.target_min:.4f}" if result.target_min is not None else "-∞"
        t_max_str = f"{result.target_max:.4f}" if result.target_max is not None else "+∞"
        nom_status = "CONFORME (CENTRE)" if c_info.get("wc_nominal_compliant", True) else "HORS INTERVALLE"
        min_status = "CONFORME" if c_info.get("wc_min_compliant", True) else "DÉPASSEMENT"
        max_status = "CONFORME" if c_info.get("wc_max_compliant", True) else "DÉPASSEMENT"

        m_min = f"{c_info.get('wc_margin_min'):+.4f} mm" if c_info.get('wc_margin_min') is not None else "-"
        m_max = f"{c_info.get('wc_margin_max'):+.4f} mm" if c_info.get('wc_margin_max') is not None else "-"
        dev_nom = f"{c_info.get('nominal_deviation'):+.4f} mm" if c_info.get('nominal_deviation') is not None else "-"

        crit_data = [
            [
                Paragraph("Critère fonctionnel", cell_header),
                Paragraph("Exigence Cible", cell_header),
                Paragraph("Valeur Calculée", cell_header),
                Paragraph("Écart / Marge", cell_header),
                Paragraph("Statut Critère", cell_header),
            ],
            [
                Paragraph("1. Borne Minimale (J_min)", cell_body),
                Paragraph(f"&ge; {t_min_str} mm", cell_body),
                Paragraph(f"{result.worst_case_minus:.4f} mm", cell_body),
                Paragraph(m_min, cell_body),
                Paragraph(f"<b>{min_status}</b>", cell_body),
            ],
            [
                Paragraph("2. Centrage Nominal (J_nom)", cell_body),
                Paragraph(f"&isin; [{t_min_str} ; {t_max_str}]", cell_body),
                Paragraph(f"{result.nominal:.4f} mm", cell_body),
                Paragraph(dev_nom, cell_body),
                Paragraph(f"<b>{nom_status}</b>", cell_body),
            ],
            [
                Paragraph("3. Borne Maximale (J_max)", cell_body),
                Paragraph(f"&le; {t_max_str} mm", cell_body),
                Paragraph(f"{result.worst_case_plus:.4f} mm", cell_body),
                Paragraph(m_max, cell_body),
                Paragraph(f"<b>{max_status}</b>", cell_body),
            ],
        ]
        crit_table = Table(crit_data, colWidths=[46 * mm, 34 * mm, 34 * mm, 34 * mm, 32 * mm])
        crit_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0284c7")),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        elements.append(crit_table)
        elements.append(Spacer(1, 4 * mm))

    # 5. Advanced Modules (Thermal & Monte Carlo if provided)
    if thermal_summary or monte_carlo_summary:
        elements.append(Paragraph("3. Synthèse des analyses avancées", h2_style))

        advanced_text = []
        if thermal_summary:
            t_serv = thermal_summary.get("t_service", 20.0)
            delta_j = thermal_summary.get("delta_j_nominal", 0.0)
            j_hot = thermal_summary.get("nominal_at_t", result.nominal)
            advanced_text.append(
                f"• <b>Comportement thermique à {t_serv:.1f} °C :</b> "
                f"Jeu nominal à chaud = <b>{j_hot:.4f} mm</b> "
                f"(dérive thermique &Delta;J = {delta_j:+.4f} mm)."
            )

        if monte_carlo_summary:
            ppm = monte_carlo_summary.get("defect_ppm", 0.0)
            cp = monte_carlo_summary.get("cp")
            cpk = monte_carlo_summary.get("cpk")
            cp_str = f", Cp={cp:.2f}, Cpk={cpk:.2f}" if cp is not None else ""
            advanced_text.append(
                f"• <b>Simulation stochastique Monte Carlo (100k tirages) :</b> "
                f"Taux de non-conformité prédit = <b>{ppm:.1f} PPM</b>{cp_str}."
            )

        for line in advanced_text:
            elements.append(Paragraph(line, body_style))
            elements.append(Spacer(1, 2 * mm))

        elements.append(Spacer(1, 4 * mm))

    # 6. Approbation Block
    elements.append(Paragraph("Visa et Approbation Qualité", h2_style))
    approb_data = [
        [
            Paragraph("<b>Établi par :</b>", meta_label),
            Paragraph("<b>Vérifié par (Projet) :</b>", meta_label),
            Paragraph("<b>Approuvé par (Qualité) :</b>", meta_label),
        ],
        [
            Paragraph(f"<br/><br/>{author}<br/>Signature :", body_style),
            Paragraph("<br/><br/>Responsable BE :<br/>Signature :", body_style),
            Paragraph("<br/><br/>Visa Assurance Qualité :<br/>Signature :", body_style),
        ],
    ]
    approb_table = Table(approb_data, colWidths=[60 * mm, 60 * mm, 60 * mm])
    approb_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(approb_table)

    # 7. Legal Disclaimer
    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))
    elements.append(Paragraph(
        "<i>Document édité par la plateforme CotaStack. Outil d'aide à la conception. "
        "L'utilisateur demeure seul responsable de la validation technique et de la conformité avant fabrication.</i>",
        meta_label,
    ))

    doc.build(elements)
    return buffer.getvalue()

# ---------------------------------------------------------------------------
# Multi-Chain PDF generation utilities
# ---------------------------------------------------------------------------

def _build_1d_chain_drawing(chain: AssemblyChain, items: list[Item], width_mm: float = 180.0) -> Drawing:
    """Create a ReportLab Drawing representing the 1-D vector stack-up of chain.

    Uses normalized bounding-box projection so all dimension vectors, the origin x=0,
    and the closure vector J_nom stay strictly within the printable boundaries.
    """
    mm_to_pt = 72.0 / 25.4  # 1 mm = 2.83464567 pt
    draw_width = width_mm * mm_to_pt

    if not items:
        # Graceful empty drawing
        draw_height = 40.0
        d = Drawing(draw_width, draw_height)
        d.add(Rect(0, 0, draw_width, draw_height, fillColor=colors.HexColor("#f8fafc"), strokeColor=colors.HexColor("#cbd5e1"), strokeWidth=0.5, rx=3, ry=3))
        d.add(String(draw_width / 2, 16, "Aucun maillon dans cette chaîne dimensionnelle.", fontSize=8, fontName="Helvetica-Oblique", fillColor=colors.HexColor("#64748b"), textAnchor="middle"))
        return d

    # 1. Compute cumulative coordinates
    current_x = 0.0
    segments = []
    points = [0.0]

    for it in items:
        start_x = current_x
        step = it.orientation * it.nominal
        end_x = start_x + step
        current_x = end_x
        segments.append((it, start_x, end_x))
        points.extend([start_x, end_x])

    points.append(current_x)

    x_min = min(points)
    x_max = max(points)
    span = x_max - x_min
    if span <= 1e-9:
        span = 1.0

    # Margins inside drawing
    pad_left = 45.0
    pad_right = 45.0
    plot_w = max(100.0, draw_width - pad_left - pad_right)

    def to_pt_x(val: float) -> float:
        return pad_left + ((val - x_min) / span) * plot_w

    # Vertical sizing
    n_links = len(items)
    row_h = 20.0
    closure_h = 24.0
    header_pad = 16.0
    draw_height = max(65.0, header_pad + n_links * row_h + closure_h + 12.0)

    drawing = Drawing(draw_width, draw_height)
    # Background panel
    drawing.add(Rect(0, 0, draw_width, draw_height, fillColor=colors.HexColor("#f8fafc"), strokeColor=colors.HexColor("#cbd5e1"), strokeWidth=0.8, rx=4, ry=4))

    # Origin line x=0
    x_origin_pt = to_pt_x(0.0)
    origin_line = Line(x_origin_pt, 8, x_origin_pt, draw_height - 6)
    origin_line.strokeColor = colors.HexColor("#94a3b8")
    origin_line.strokeWidth = 0.8
    origin_line.strokeDashArray = [2, 2]
    drawing.add(origin_line)
    drawing.add(String(x_origin_pt, draw_height - 10, "0", fontSize=5.5, fontName="Helvetica-Bold", fillColor=colors.HexColor("#64748b"), textAnchor="middle"))

    pos_color = colors.HexColor("#0284c7")  # Cyan/Blue for +
    neg_color = colors.HexColor("#ea580c")  # Orange/Red for -
    closure_color = colors.HexColor("#059669")  # Emerald Green for closure

    # Draw chain links from top to bottom
    for idx, (it, start_x, end_x) in enumerate(segments):
        y_pos = draw_height - header_pad - (idx + 1) * row_h + 5.0
        x1 = to_pt_x(start_x)
        x2 = to_pt_x(end_x)

        col = pos_color if it.orientation > 0 else neg_color
        # Horizontal vector bar
        vec_line = Line(x1, y_pos, x2, y_pos)
        vec_line.strokeColor = col
        vec_line.strokeWidth = 1.8
        drawing.add(vec_line)

        # Arrowhead at x2
        arrow_len = 4.5
        arrow_w = 2.5
        if it.orientation > 0:
            arrow = Polygon(points=[
                x2, y_pos,
                x2 - arrow_len, y_pos + arrow_w,
                x2 - arrow_len, y_pos - arrow_w,
            ])
        else:
            arrow = Polygon(points=[
                x2, y_pos,
                x2 + arrow_len, y_pos + arrow_w,
                x2 + arrow_len, y_pos - arrow_w,
            ])
        arrow.fillColor = col
        arrow.strokeColor = col
        drawing.add(arrow)

        # Subtle vertical tick at start_x
        tick = Line(x1, y_pos - 2.5, x1, y_pos + 2.5)
        tick.strokeColor = col
        tick.strokeWidth = 0.8
        drawing.add(tick)

        # Label above vector (compact text & clamped to prevent overflow)
        mid_x = (x1 + x2) / 2.0
        # Clamp text position strictly within drawing bounds
        margin_safe = 40.0
        mid_x = max(margin_safe, min(draw_width - margin_safe, mid_x))
        sign_char = "+" if it.orientation > 0 else "-"
        lbl = f"#{idx+1} {it.name[:13]} ({sign_char}{it.nominal:.2f})"
        drawing.add(String(mid_x, y_pos + 3.0, lbl, fontSize=6, fontName="Helvetica-Bold", fillColor=col, textAnchor="middle"))

    # Closure Game vector (J_nom) at the bottom
    y_closure = 14.0
    x_c_start = to_pt_x(0.0)
    x_c_end = to_pt_x(current_x)

    c_line = Line(x_c_start, y_closure, x_c_end, y_closure)
    c_line.strokeColor = closure_color
    c_line.strokeWidth = 2.0
    c_line.strokeDashArray = [3, 2]
    drawing.add(c_line)

    c_arrow_len = 5.0
    c_arrow_w = 3.0
    if current_x >= 0:
        c_arrow = Polygon(points=[
            x_c_end, y_closure,
            x_c_end - c_arrow_len, y_closure + c_arrow_w,
            x_c_end - c_arrow_len, y_closure - c_arrow_w,
        ])
    else:
        c_arrow = Polygon(points=[
            x_c_end, y_closure,
            x_c_end + c_arrow_len, y_closure + c_arrow_w,
            x_c_end + c_arrow_len, y_closure - c_arrow_w,
        ])

    c_arrow.fillColor = closure_color
    c_arrow.strokeColor = closure_color
    drawing.add(c_arrow)

    # Closure text
    mid_c_x = (x_c_start + x_c_end) / 2.0
    mid_c_x = max(55.0, min(draw_width - 55.0, mid_c_x))
    closure_lbl = f"FERMETURE : J_nom = {current_x:+.3f} mm"
    drawing.add(String(mid_c_x, y_closure + 3.5, closure_lbl, fontSize=6.5, fontName="Helvetica-Bold", fillColor=closure_color, textAnchor="middle"))

    return drawing



def generate_multi_chain_pdf_report(
    project: MultiChainProject,
    project_metadata: dict[str, Any] | None = None,
) -> bytes:
    """Generate a complete multi-chain A4 PDF report as raw bytes.

    Includes:
    1. Cartouche & project identification.
    2. Global system summary (KPIs, shared pivot parts).
    3. Global chains summary table.
    4. Detailed technical sections per chain (1D vector drawing, items table, WC & RSS results).
    5. Quality assurance visa & legal disclaimer.
    """
    meta = project_metadata or {}
    proj_title = html.escape(str(meta.get("title", project.name or "Système Multi-Chaînes")))
    author = html.escape(str(meta.get("author", "Bureau d'Études Mécanique")))
    revision = html.escape(str(meta.get("revision", "A")))
    today_str = html.escape(str(meta.get("date", str(date.today()))))

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    primary_color = colors.HexColor("#0284c7")
    dark_color = colors.HexColor("#0f172a")

    title_style = ParagraphStyle("MultiTitle", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=primary_color)
    h2_style = ParagraphStyle("MultiH2", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=dark_color, spaceBefore=8, spaceAfter=4)
    h3_style = ParagraphStyle("MultiH3", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=primary_color, spaceBefore=5, spaceAfter=3)
    body_style = ParagraphStyle("MultiBody", parent=styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=dark_color)
    meta_label = ParagraphStyle("MultiMetaLabel", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=colors.HexColor("#475569"))
    meta_val = ParagraphStyle("MultiMetaVal", parent=styles["Normal"], fontName="Helvetica", fontSize=7, leading=9, textColor=dark_color)
    cell_header = ParagraphStyle("MultiCellHeader", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=6.8, leading=8.5, textColor=colors.white, alignment=1)
    cell_body = ParagraphStyle("MultiCellBody", parent=styles["Normal"], fontName="Helvetica", fontSize=6.8, leading=8.5, textColor=dark_color, alignment=1)

    elements: list[Any] = []

    # 1. Header & Cartouche
    elements.append(Paragraph(f"📐 CotaStack — {proj_title}", title_style))
    elements.append(Paragraph("Dossier de Tolérancement Système Multi-Chaînes 1D — Conforme ISO GPS", body_style))
    elements.append(Spacer(1, 6 * mm))

    cartouche_data = [
        [
            Paragraph("Projet Système :", meta_label),
            Paragraph(f"<b>{proj_title}</b>", meta_val),
            Paragraph("Indice Rév. :", meta_label),
            Paragraph(f"<b>{revision}</b>", meta_val),
        ],
        [
            Paragraph("Auteur / BE :", meta_label),
            Paragraph(author, meta_val),
            Paragraph("Date d'édition :", meta_label),
            Paragraph(today_str, meta_val),
        ],
    ]
    cartouche_table = Table(cartouche_data, colWidths=[30 * mm, 60 * mm, 25 * mm, 65 * mm])
    cartouche_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(cartouche_table)
    elements.append(Spacer(1, 6 * mm))

    # 2. System Global Health Summary
    elements.append(Paragraph("1. Synthèse globale du système mécanique", h2_style))
    summary = project.get_system_summary()

    pivot_str = ", ".join(summary.critical_pivot_parts) if summary.critical_pivot_parts else "Aucune (chaînes découplées)"
    wc_status_str = f"{summary.wc_compliant_count} / {summary.total_chains} conformes"
    nok_str = f"{summary.non_compliant_count} chaîne(s)"

    kpi_data = [
        [
            Paragraph("Total chaînes d'assemblage :", meta_label),
            Paragraph(f"<b>{summary.total_chains}</b>", meta_val),
            Paragraph("Chaînes conformes Pire des Cas :", meta_label),
            Paragraph(f"<b>{wc_status_str}</b>", meta_val),
        ],
        [
            Paragraph("Chaînes critiques non-conformes :", meta_label),
            Paragraph(f"<font color='#dc2626'><b>{nok_str}</b></font>" if summary.non_compliant_count > 0 else "<b>0 (100% GO)</b>", meta_val),
            Paragraph("Pièces pivots partagées :", meta_label),
            Paragraph(html.escape(pivot_str), meta_val),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[45 * mm, 45 * mm, 45 * mm, 45 * mm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 5 * mm))

    # 3. All-Chains Summary Table
    elements.append(Paragraph("Tableau récapitulatif des chaînes d'assemblage", h3_style))
    sum_headers = [
        Paragraph("Chaîne", cell_header),
        Paragraph("ID", cell_header),
        Paragraph("J_nom (mm)", cell_header),
        Paragraph("Pire des Cas [Min ; Max] (mm)", cell_header),
        Paragraph("Dispersion IT_WC (mm)", cell_header),
        Paragraph("Cible fonctionnelle", cell_header),
        Paragraph("Verdict Pire des Cas", cell_header),
    ]
    sum_rows = [sum_headers]

    for status in summary.chains_status:
        c = project.get_chain(status.chain_id)
        if c.target_min is not None or c.target_max is not None:
            t_str = f"[{c.target_min if c.target_min is not None else '-∞'} ; {c.target_max if c.target_max is not None else '+∞'}]"
        else:
            t_str = "Non spécifiée"

        it_wc_disp = status.result.worst_case_plus - status.result.worst_case_minus
        sum_rows.append([
            Paragraph(html.escape(status.name), cell_body),
            Paragraph(html.escape(status.chain_id), cell_body),
            Paragraph(f"{status.result.nominal:.4f}", cell_body),
            Paragraph(f"[{status.result.worst_case_minus:.3f} ; {status.result.worst_case_plus:.3f}]", cell_body),
            Paragraph(f"{it_wc_disp:.3f}", cell_body),
            Paragraph(t_str, cell_body),
            Paragraph(f"<b>{html.escape(status.wc_status_label)}</b>", cell_body),
        ])

    if len(sum_rows) == 1:
        sum_rows.append([Paragraph("<i>Aucune chaîne dans le projet</i>", cell_body)] * 7)

    summary_table = Table(sum_rows, colWidths=[38 * mm, 20 * mm, 20 * mm, 36 * mm, 24 * mm, 24 * mm, 18 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), dark_color),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 5 * mm))

    # 4. Detailed Sections for Each Chain (Each chain block kept together to avoid splitting)
    for idx_chain, (c_id, chain) in enumerate(project.chains.items(), start=1):
        chain_flowables = []
        chain_flowables.append(Paragraph(f"2.{idx_chain} Chaîne : {html.escape(chain.name)} [{html.escape(chain.id)}]", h2_style))

        if chain.description:
            chain_flowables.append(Paragraph(f"<i>Description : {html.escape(chain.description)}</i>", body_style))
            chain_flowables.append(Spacer(1, 2 * mm))

        # Target specification
        if chain.target_min is not None or chain.target_max is not None:
            t_min_str = f"{chain.target_min:.3f} mm" if chain.target_min is not None else "-∞"
            t_max_str = f"{chain.target_max:.3f} mm" if chain.target_max is not None else "+∞"
            chain_flowables.append(Paragraph(f"<b>Spécification fonctionnelle cible :</b> Jeu requis &isin; [{t_min_str} ; {t_max_str}]", body_style))
            chain_flowables.append(Spacer(1, 3 * mm))

        # Resolve items
        items = project.resolve_chain_items(chain.id) if chain.links else []

        # Vector stack diagram (Drawing)
        chain_flowables.append(Paragraph("<b>Tracé vectoriel 1D de la boucle de tolérance :</b>", h3_style))
        drawing = _build_1d_chain_drawing(chain, items)
        chain_flowables.append(drawing)
        chain_flowables.append(Spacer(1, 4 * mm))

        # Table of dimensions (items)
        chain_flowables.append(Paragraph("<b>Tableau des cotes et maillons dimensionnels :</b>", h3_style))
        item_headers = [
            Paragraph("Repère / Cote", cell_header),
            Paragraph("Sens", cell_header),
            Paragraph("Nominal (mm)", cell_header),
            Paragraph("EI (mm)", cell_header),
            Paragraph("ES (mm)", cell_header),
            Paragraph("IT (mm)", cell_header),
            Paragraph("Cote moy. (mm)", cell_header),
            Paragraph("Matériau", cell_header),
        ]
        item_rows = [item_headers]

        for it in items:
            sign_str = "+" if it.orientation > 0 else "-"
            mat_str = it.material or "Acier"
            safe_name = html.escape(str(it.name))
            safe_mat = html.escape(str(mat_str.split()[0]))
            item_rows.append([
                Paragraph(safe_name, cell_body),
                Paragraph(sign_str, cell_body),
                Paragraph(f"{it.nominal:.4f}", cell_body),
                Paragraph(f"{it.ei:+.4f}", cell_body),
                Paragraph(f"{it.es:+.4f}", cell_body),
                Paragraph(f"{it.IT:.4f}", cell_body),
                Paragraph(f"{it.L_moy:.4f}", cell_body),
                Paragraph(safe_mat, cell_body),
            ])

        if not items:
            item_rows.append([Paragraph("<i>Aucun maillon dans cette chaîne</i>", cell_body)] * 8)

        items_table = Table(item_rows, colWidths=[36 * mm, 12 * mm, 22 * mm, 18 * mm, 18 * mm, 18 * mm, 24 * mm, 32 * mm])
        items_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), primary_color),
            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ]))
        chain_flowables.append(items_table)
        chain_flowables.append(Spacer(1, 4 * mm))

        # Calculation Results (Worst-Case)
        if items:
            calc = ChainCalculator(items, target_min=chain.target_min, target_max=chain.target_max)
            result = calc.calculate()
            it_wc = sum(it.IT for it in items)
            c_info = result.compliance
            wc_comp = "CONFORME (GO)" if c_info.get("wc_compliant", True) else "NON CONFORME (NO-GO)"

            # Detail 3 criteria
            min_st = "OK" if c_info.get("wc_min_compliant", True) else "DÉPASSEMENT"
            nom_st = "OK" if c_info.get("wc_nominal_compliant", True) else "DÉCENTRÉ"
            max_st = "OK" if c_info.get("wc_max_compliant", True) else "DÉPASSEMENT"
            crit_3_summary = f"{wc_comp} [Min: {min_st}, Nom: {nom_st}, Max: {max_st}]"

            res_data = [
                [
                    Paragraph("Méthode de calcul", cell_header),
                    Paragraph("Jeu Min (mm)", cell_header),
                    Paragraph("Jeu Moyen (mm)", cell_header),
                    Paragraph("Jeu Max (mm)", cell_header),
                    Paragraph("IT Résultant (mm)", cell_header),
                    Paragraph("Verdict 3 critères (Min/Nom/Max)", cell_header),
                ],
                [
                    Paragraph("<b>Pire des Cas (Worst-Case)</b>", cell_body),
                    Paragraph(f"{result.worst_case_minus:.4f}", cell_body),
                    Paragraph(f"{result.mean:.4f}", cell_body),
                    Paragraph(f"{result.worst_case_plus:.4f}", cell_body),
                    Paragraph(f"{it_wc:.4f}", cell_body),
                    Paragraph(f"<b>{crit_3_summary}</b>", cell_body),
                ],
            ]
            res_table = Table(res_data, colWidths=[42 * mm, 24 * mm, 24 * mm, 24 * mm, 24 * mm, 42 * mm])
            res_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), dark_color),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 2.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ]))
            chain_flowables.append(res_table)

        chain_flowables.append(Spacer(1, 6 * mm))

        # Use KeepTogether so individual chain blocks do not get cut across page boundaries unless too large
        elements.append(KeepTogether(chain_flowables))

    # 5. Quality Visa & Legal Disclaimer (Final Block)
    visa_flowables = [
        Paragraph("Visa et Approbation Qualité", h2_style),
        Spacer(1, 2 * mm),
    ]
    approb_data = [
        [
            Paragraph("<b>Établi par :</b>", meta_label),
            Paragraph("<b>Vérifié par (Projet) :</b>", meta_label),
            Paragraph("<b>Approuvé par (Qualité) :</b>", meta_label),
        ],
        [
            Paragraph(f"<br/><br/>{author}<br/>Signature :", body_style),
            Paragraph("<br/><br/>Responsable Bureau d'Études :<br/>Signature :", body_style),
            Paragraph("<br/><br/>Assurance Qualité & Conformité :<br/>Signature :", body_style),
        ],
    ]
    approb_table = Table(approb_data, colWidths=[60 * mm, 60 * mm, 60 * mm])
    approb_table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#94a3b8")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    visa_flowables.append(approb_table)
    visa_flowables.append(Spacer(1, 6 * mm))
    elements.append(KeepTogether(visa_flowables))

    elements.append(Spacer(1, 6 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=4))
    elements.append(Paragraph(
        "<i>Document édité par la plateforme CotaStack. Outil d'aide à la conception et au tolérancement mécanique 1D. "
        "L'utilisateur demeure seul responsable de la validation technique et de la conformité dimensionnelle avant fabrication.</i>",
        meta_label,
    ))

    doc.build(elements)
    return buffer.getvalue()


