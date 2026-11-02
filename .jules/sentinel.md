# Sentinel's Journal

## 2025-05-18 - ReportLab Paragraph Markup Injection and DoS via Unescaped User Input
**Vulnerability:** In `backend/report_generator.py`, user-controlled strings (project title, author, revision, date, item name, material) were passed directly into ReportLab `Paragraph` flowables without sanitization. In ReportLab, `Paragraph` parses contents as XML markup; strings with unescaped `<`, `>`, or `&` cause parser crashes (`ValueError: paraparser: syntax error`), leading to Denial of Service when generating PDF reports, as well as unintended formatting or link injection.
**Learning:** ReportLab `Paragraph` flowables do not auto-escape input strings like plain text canvas operations do; any user input included in `Paragraph` must be explicitly escaped with `html.escape` (or `xml.sax.saxutils.escape`).
**Prevention:** Always escape dynamic or user-supplied strings before interpolating them into ReportLab `Paragraph` calls.

## 2026-11-01 - XSS via Unescaped Component Identifier in Streamlit HTML Badge
**Vulnerability:** In `pages/04_Multi_Chaines.py`, the component identifier `link.part_id` was interpolated directly into an HTML snippet (`source_badge`) rendered via `st.markdown(..., unsafe_allow_html=True)`. If a user imported a malicious `.cotastack_multi.json` project containing crafted HTML/JavaScript in `part_id` (or manipulated local catalog entries), arbitrary HTML and JavaScript could be executed in the user's browser session.
**Learning:** In Streamlit, rendering markdown with `unsafe_allow_html=True` disables sanitization. Any dynamic, user-controllable, or file-loaded variable interpolated into raw HTML snippets must be sanitized with `html.escape`.
**Prevention:** Always wrap any variable interpolated into `unsafe_allow_html=True` markdown blocks with `html.escape`.

## 2026-11-01 - SSRF and URL Manipulation via Unvalidated GitHub Repository Parameter
**Vulnerability:** In `backend/feedback.py`, functions `build_github_issue_url` and `submit_github_issue` accepted a `repo` string argument without format or path validation. If an attacker supplied path traversal sequences (e.g. `../...`), query strings, fragments, or a rogue endpoint, requests could be redirected or arbitrary GitHub API endpoints could be invoked with the authenticated user's bearer token, creating Server-Side Request Forgery (SSRF) and URL injection risks.
**Learning:** External API integrations that construct target endpoints dynamically from user-controllable or configuration parameters must strictly enforce a canonical whitelist or regex structure before constructing URLs or making HTTP requests.
**Prevention:** Always validate repository or resource paths with a strict regular expression matching canonical patterns (e.g. `^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+$`) prior to URL interpolation.
