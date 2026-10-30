"""CotaStack - Rapports & Exportation."""

import streamlit as st
import pandas as pd
from datetime import date
from backend.models import Item
from backend.calculator import ChainCalculator
from backend.report_generator import generate_pdf_report


st.set_page_config(page_title="Rapports — CotaStack", page_icon="📄", layout="wide")


def dataframe_to_items(df: pd.DataFrame) -> list[Item]:
    """Convert session DataFrame to list of Items."""
    items = []
    for _, row in df.iterrows():
        name = str(row.get("Repère", "")).strip()
        if not name:
            continue

        raw_orient = row.get("Orientation", "+")
        if isinstance(raw_orient, str):
            orientation = -1 if raw_orient.strip() == "-" else 1
        else:
            try:
                orientation = -1 if int(raw_orient) < 0 else 1
            except (ValueError, TypeError):
                orientation = 1

        try:
            nominal = float(row.get("Nominal (mm)", 0.0))
            es = float(row.get("ES (mm)", 0.0))
            ei = float(row.get("EI (mm)", 0.0))
        except (ValueError, TypeError):
            continue

        if es < ei:
            es, ei = ei, es

        material = str(row.get("Matériau", "Acier (standard)"))

        items.append(Item(
            name=name,
            nominal=nominal,
            es=es,
            ei=ei,
            orientation=orientation,  # type: ignore
            material=material,
        ))
    return items


def main():
    st.title("📄 Rapports & Certification Documentaire")
    st.caption("Édition de notes de calcul normées A4 (PDF), exports légers et visa qualité")

    # Check session data
    has_data = "items_df" in st.session_state and not st.session_state.items_df.empty
    items = dataframe_to_items(st.session_state.items_df) if has_data else []

    col_cartouche, col_export = st.columns([1, 1])

    with col_cartouche:
        st.subheader("🏷️ Cartouche d'identification")
        proj_name = st.text_input("Titre du projet / Étude", value="Assemblage Guidage Arbre-Carter")
        author_name = st.text_input("Ingénieur d'études / BE", value="Bureau d'Études Mécanique")
        rev = st.text_input("Indice de révision", value="A")
        calc_date = st.date_input("Date de validation", value=date.today())

    with col_export:
        st.subheader("📦 Options d'export")

        if not items:
            st.warning("Aucune chaîne active dans le calculateur. Rendez-vous sur la page **🧮 Calculateur** pour saisir vos maillons.")
        else:
            calc = ChainCalculator(
                items,
                target_min=st.session_state.get("target_min"),
                target_max=st.session_state.get("target_max"),
            )
            result = calc.calculate()

            # Official PDF Export
            mc_dict = {
                "defect_ppm": st.session_state.mc_res.defect_ppm if "mc_res" in st.session_state else 0.0,
                "cp": st.session_state.mc_res.cp if "mc_res" in st.session_state else None,
                "cpk": st.session_state.mc_res.cpk if "mc_res" in st.session_state else None,
            } if "mc_res" in st.session_state else None

            pdf_bytes = generate_pdf_report(
                items=items,
                result=result,
                project_metadata={
                    "title": proj_name,
                    "author": author_name,
                    "revision": rev,
                    "date": str(calc_date),
                },
                monte_carlo_summary=mc_dict,
            )

            st.download_button(
                label="📄 Télécharger le Rapport Officiel (PDF A4)",
                data=pdf_bytes,
                file_name=f"note_calcul_{proj_name.lower().replace(' ', '_')}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True,
            )

            # CSV Export
            csv_bytes = st.session_state.items_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Exporter le tableau brut (CSV)",
                data=csv_bytes,
                file_name=f"{proj_name.lower().replace(' ', '_')}_cotes.csv",
                mime="text/csv",
                use_container_width=True,
            )

            # Markdown Report Generation
            report_lines = [
                f"# Note de calcul de chaîne de cotes 1D — {proj_name}",
                f"- **Auteur** : {author_name}",
                f"- **Date** : {calc_date}",
                f"- **Révision** : {rev}",
                "",
                "## 1. Données dimensionnelles d'entrée",
                "| Repère | Sens | Nominal (mm) | EI (mm) | ES (mm) | IT (mm) | L_moy (mm) | Matériau |",
                "|:-------|:----:|:------------:|:-------:|:-------:|:-------:|:----------:|:--------:|",
            ]
            for it in items:
                sign = "+" if it.orientation > 0 else "-"
                mat_short = (it.material or "Acier").split()[0]
                report_lines.append(
                    f"| {it.name} | {sign} | {it.nominal:.4f} | {it.ei:+.4f} | {it.es:+.4f} | {it.IT:.4f} | {it.L_moy:.4f} | {mat_short} |"
                )

            it_wc = sum(i.IT for i in items)
            it_rss = (sum(i.IT**2 for i in items))**0.5

            report_lines.extend([
                "",
                "## 2. Résultats de calcul 1D",
                f"- **Jeu nominal calculé ($J_{{nom}}$)** : `{result.nominal:.4f} mm`",
                f"- **Jeu moyen calculé ($J_{{moy}}$)** : `{result.mean:.4f} mm`",
                f"- **Pire des cas (WC)** : `[{result.worst_case_minus:.4f} ; {result.worst_case_plus:.4f}] mm` (IT = {it_wc:.4f} mm)",
                f"- **Statistique RSS (3σ)** : `[{result.rss_minus:.4f} ; {result.rss_plus:.4f}] mm` (IT = {it_rss:.4f} mm)",
            ])

            if result.target_min is not None or result.target_max is not None:
                report_lines.append("")
                report_lines.append("## 3. Évaluation de conformité vis-à-vis des exigences")
                if result.target_min is not None:
                    report_lines.append(f"- Exigence Jeu minimal : `{result.target_min:.4f} mm`")
                if result.target_max is not None:
                    report_lines.append(f"- Exigence Jeu maximal : `{result.target_max:.4f} mm`")
                report_lines.append(f"- Verdict Pire des Cas : **{'CONFORME (GO)' if result.compliance['wc_compliant'] else 'NON CONFORME (NO-GO)'}**")
                report_lines.append(f"- Verdict Statistique RSS : **{'CONFORME (GO)' if result.compliance['rss_compliant'] else 'NON CONFORME (NO-GO)'}**")

            report_lines.extend([
                "",
                "## 4. Visa de validation",
                "| Rédacteur | Approbateur Qualité | Décision |",
                "|:---------:|:-------------------:|:--------:|",
                f"| {author_name} | ___________________ | {'APPROUVÉ' if result.compliance.get('rss_compliant', True) else 'REFUSÉ'} |",
                "",
                "---",
                "*Rapport édité par CotaStack — Conforme aux exigences de cotation fonctionnelle ISO GPS.*",
            ])
            full_md_report = "\n".join(report_lines)

            st.download_button(
                label="📥 Exporter la note complète (Markdown)",
                data=full_md_report,
                file_name=f"note_calcul_{proj_name.lower().replace(' ', '_')}.md",
                mime="text/markdown",
                use_container_width=True,
            )

    if items:
        st.divider()
        st.subheader("👁️ Aperçu de la note de calcul")
        st.markdown(full_md_report)

    # --- Disclaimer ---
    st.divider()
    st.warning(
        "⚠️ **Avertissement** : Outil d'aide à la conception. "
        "L'utilisateur demeure seul responsable de la validation technique avant fabrication."
    )


if __name__ == "__main__":
    main()
