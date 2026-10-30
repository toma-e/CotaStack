"""PDF calculation note generator for CotaStack using ReportLab.

Produces clean, standardized A4 PDF calculation sheets for mechanical engineering
design reviews and quality records.
"""

import io
from datetime import date
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
)

from backend.models import Item, ChainResult


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

    meta = project_metadata or {}
    proj_title = meta.get("title", "Chaîne de cotes 1D — Note de calcul")
    author = meta.get("author", "Bureau d'Études Mécanique")
    revision = meta.get("revision", "A")
    today_str = meta.get("date", str(date.today()))

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
        table_rows.append([
            Paragraph(item.name, cell_body),
            Paragraph(sign_str, cell_body),
            Paragraph(f"{item.nominal:.4f}", cell_body),
            Paragraph(f"{item.ei:+.4f}", cell_body),
            Paragraph(f"{item.es:+.4f}", cell_body),
            Paragraph(f"{item.IT:.4f}", cell_body),
            Paragraph(f"{item.L_moy:.4f}", cell_body),
            Paragraph(mat_str.split()[0], cell_body),
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

    # 4. Results Section
    elements.append(Paragraph("2. Bilan des résultats de calcul 1D", h2_style))

    it_wc = sum(it.IT for it in items)
    it_rss = (sum(it.IT ** 2 for it in items)) ** 0.5

    wc_comp_str = "CONFORME (GO)" if result.compliance.get("wc_compliant", True) else "NON CONFORME (NO-GO)"
    rss_comp_str = "CONFORME (GO)" if result.compliance.get("rss_compliant", True) else "NON CONFORME (NO-GO)"

    results_data = [
        [
            Paragraph("Méthode", cell_header),
            Paragraph("Jeu Min (mm)", cell_header),
            Paragraph("Jeu Moyen (mm)", cell_header),
            Paragraph("Jeu Max (mm)", cell_header),
            Paragraph("IT Total (mm)", cell_header),
            Paragraph("Verdict Cible", cell_header),
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
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(res_table)
    elements.append(Spacer(1, 6 * mm))

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
