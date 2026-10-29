"""Shared pieces of the issue-to-registry scripts.

Both `pp_from_issue.py` and `pss_from_issue.py` read an issue body produced by
one of the forms in .github/ISSUE_TEMPLATE, download the attached PDF and edit
registry.md. Everything they handle comes from a public issue, so nothing here
is trusted: the attachment host is checked against an allow list, the download
is size-capped and must start with a PDF header, and every value that reaches
registry.md is validated.
"""

import os
import re
import urllib.parse
import urllib.request

ALLOWED_HOSTS = {
    "github.com",
    "objects.githubusercontent.com",
    "user-images.githubusercontent.com",
    "raw.githubusercontent.com",
}
MAX_PDF_BYTES = 25 * 1024 * 1024

SECTION = re.compile(r"^###\s+(.*\S)\s*$")
HEADING = re.compile(r"^##\s+(\S+)\s+(.*\S)\s*$")
PROJECT_ID = re.compile(r"^AU(\d{4})$")
RELEASE = re.compile(r"^R\d+$", re.IGNORECASE)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
URL = re.compile(r"https://[^\s)>\]]+")

NO_RESPONSE = "_No response_"


def fail(message):
    raise SystemExit("error: " + message)


def parse_issue(body, fields, required):
    """Split a rendered issue-form body into {name: value} using `fields`.

    `fields` maps the form's field labels to the names used by the caller.
    """
    values = {}
    key = None
    buf = []
    for line in body.splitlines():
        section = SECTION.match(line)
        if section:
            if key:
                values[key] = "\n".join(buf).strip()
            key = fields.get(section.group(1).strip())
            buf = []
            continue
        if key:
            buf.append(line)
    if key:
        values[key] = "\n".join(buf).strip()
    for name in required:
        if not values.get(name) or values[name] == NO_RESPONSE:
            fail("the issue is missing a value for %r" % name)
    return values


def optional(values, name):
    """A field's value, or "" when the submitter left it blank."""
    value = values.get(name, "")
    return "" if value == NO_RESPONSE else value


def clean(value, what):
    """A single line, safe to put in a markdown table cell."""
    value = " ".join(value.split())
    if "|" in value:
        fail("%s may not contain a '|'" % what)
    if not value:
        fail("%s is empty" % what)
    return value


def check_date(value, what):
    if not DATE.match(value):
        fail("%s must be YYYY-MM-DD - got %r" % (what, value))
    return value


def attachment_url(text, what):
    """The first allowed GitHub attachment URL in a document field."""
    for candidate in URL.findall(text):
        host = urllib.parse.urlparse(candidate).hostname or ""
        if host in ALLOWED_HOSTS:
            return candidate
    fail(
        "no GitHub attachment found in the %s field - drag the PDF into the "
        "box so GitHub uploads it" % what
    )


def download_pdf(url, dest):
    request = urllib.request.Request(url, headers={"User-Agent": "hl7au-projects-registry"})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES:
        fail("the attachment is larger than %d MB" % (MAX_PDF_BYTES // (1024 * 1024)))
    if not data.startswith(b"%PDF-"):
        fail("the attachment is not a PDF - submit the approved PDF, not a Word document")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    return len(data)


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return f.read().splitlines()


def write_lines(path, lines):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def read_projects(lines):
    """[(index of the '##' line, id, title)] for each project in registry.md."""
    return [
        (i, m.group(1), m.group(2))
        for i, line in enumerate(lines)
        for m in [HEADING.match(line)]
        if m
    ]


def find_project(projects, wanted):
    key = wanted.casefold()
    for index, pid, title in projects:
        if pid.casefold() == key or title.casefold() == key:
            return index, pid, title
    return None


def next_project_id(projects):
    """One past the highest AU#### in the registry."""
    numbers = [int(m.group(1)) for _, pid, _ in projects for m in [PROJECT_ID.match(pid)] if m]
    return "AU%04d" % (max(numbers) + 1 if numbers else 1)


def section_bounds(lines, start):
    """The half-open line range of the project section beginning at `start`."""
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if HEADING.match(lines[i]):
            end = i
            break
    while end > start and not lines[end - 1].strip():
        end -= 1
    return start, end


def cells(line):
    """The cells of a markdown table row, or None if the line is not one."""
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None
    parts = [c.strip() for c in stripped[1:-1].split("|")]
    if len(parts) != 5 or parts[0].lower() == "release" or set(parts[0]) <= {"-", ":"}:
        return None
    return parts


def releases(section):
    """The releases of every PSS row in a project's section, in order."""
    return [c[0] for c in (cells(line) for line in section) if c]


def find_release(lines, start, end, release):
    """The index of the PSS row for `release`, or None."""
    for i in range(start, end):
        c = cells(lines[i])
        if c and c[0].casefold() == release.casefold():
            return i
    return None


def set_cell(lines, i, column, value):
    """Replace one cell of the PSS row at `i`."""
    c = cells(lines[i])
    c[column] = value
    lines[i] = "| %s |" % " | ".join(c)


def short_name(title):
    """The short form used in file names: "... FHIR Implementation Guide" -> "... FHIR IG"."""
    stem = re.sub(r"\bFHIR Implementation Guide\b", "FHIR IG", title, flags=re.IGNORECASE)
    return re.sub(r"\bImplementation Guide\b", "IG", stem, flags=re.IGNORECASE)


def document_stem(title, section):
    """The file-name stem for a project: from its own documents, else its title.

    Existing PDFs carry the short form of the name ("AU Core FHIR IG"), which
    is not always derivable from the registry title, so reuse the project's own
    file names when it has any. Returns (stem, taken_from_a_file).
    """
    for line in reversed(section):
        match = re.search(r"PSS/\d{8}\s+(.*?)\s+R\d+\.pdf", line, re.IGNORECASE)
        if match:
            return match.group(1), True
    for line in section:
        match = re.match(r"\s*PP:\s*PP/\d{8}\s+(.*?)\.pdf\s*$", line, re.IGNORECASE)
        if match:
            return match.group(1), True
    return short_name(title), False


def summary_table(rows):
    return ["| Field | Value |", "| --- | --- |"] + ["| %s | %s |" % r for r in rows]
