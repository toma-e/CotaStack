# Sentinel's Journal

## 2025-05-18 - ReportLab Paragraph Markup Injection and DoS via Unescaped User Input
**Vulnerability:** In `backend/report_generator.py`, user-controlled strings (project title, author, revision, date, item name, material) were passed directly into ReportLab `Paragraph` flowables without sanitization. In ReportLab, `Paragraph` parses contents as XML markup; strings with unescaped `<`, `>`, or `&` cause parser crashes (`ValueError: paraparser: syntax error`), leading to Denial of Service when generating PDF reports, as well as unintended formatting or link injection.
**Learning:** ReportLab `Paragraph` flowables do not auto-escape input strings like plain text canvas operations do; any user input included in `Paragraph` must be explicitly escaped with `html.escape` (or `xml.sax.saxutils.escape`).
**Prevention:** Always escape dynamic or user-supplied strings before interpolating them into ReportLab `Paragraph` calls.
