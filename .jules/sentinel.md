# Sentinel's Journal

## 2025-05-18 - ReportLab Paragraph Markup Injection and DoS via Unescaped User Input
**Vulnerability:** In `backend/report_generator.py`, user-controlled strings (project title, author, revision, date, item name, material) were passed directly into ReportLab `Paragraph` flowables without sanitization. In ReportLab, `Paragraph` parses contents as XML markup; strings with unescaped `<`, `>`, or `&` cause parser crashes (`ValueError: paraparser: syntax error`), leading to Denial of Service when generating PDF reports, as well as unintended formatting or link injection.
**Learning:** ReportLab `Paragraph` flowables do not auto-escape input strings like plain text canvas operations do; any user input included in `Paragraph` must be explicitly escaped with `html.escape` (or `xml.sax.saxutils.escape`).
**Prevention:** Always escape dynamic or user-supplied strings before interpolating them into ReportLab `Paragraph` calls.

## 2026-11-01 - XSS via Unescaped Component Identifier in Streamlit HTML Badge
**Vulnerability:** In `pages/04_Multi_Chaines.py`, the component identifier `link.part_id` was interpolated directly into an HTML snippet (`source_badge`) rendered via `st.markdown(..., unsafe_allow_html=True)`. If a user imported a malicious `.cotastack_multi.json` project containing crafted HTML/JavaScript in `part_id` (or manipulated local catalog entries), arbitrary HTML and JavaScript could be executed in the user's browser session.
**Learning:** In Streamlit, rendering markdown with `unsafe_allow_html=True` disables sanitization. Any dynamic, user-controllable, or file-loaded variable interpolated into raw HTML snippets must be sanitized with `html.escape`.
**Prevention:** Always wrap any variable interpolated into `unsafe_allow_html=True` markdown blocks with `html.escape`.
