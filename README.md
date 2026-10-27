# HL7 AU Project Registry

A simple registry of HL7 Australia projects: each project proposal (PP) with its child
project scope statements (PSS), rendered as a single HTML page with the source PDFs.

## Contents

| Path | What it holds |
| --- | --- |
| `registry.md` | The source of truth — projects, scope statements, statuses and document links |
| `build.py` | Generates `index.html` from `registry.md` (standard library only) |
| `PP/` | Project proposal PDFs |
| `PSS/` | Project scope statement PDFs |
| `NIB/` | Notice of intent to ballot PDFs |
| `TEMPLATES/` | The blank HL7 AU forms (`.docx`, so they stay fillable) |

`index.html` is generated and is not committed — CI builds it, and you build it locally
when you want to look at it.

## Editing the registry

Edit `registry.md`, then:

```bash
python build.py
```

Open `index.html` in a browser. Clicking a project row expands its scope statements, and
clicking a document icon previews that PDF in the right-hand pane.

`build.py` prints a warning for any status outside the allowed list and for any PP/PSS
link that does not resolve to a file in the repository. CI fails the build on either.

### registry.md format

One `##` heading per project, `## <Project ID> <Title>`, followed by its fields and an
optional table of scope statements:

```markdown
## AU0010 AU eRequesting FHIR Implementation Guide

Status: Approved
Submitted: 2023-11-27
PP: PP/20231123 AU eRequesting FHIR IG.pdf

| Submitted | Status | Title | PSS |
| --- | --- | --- | --- |
| 2025-04-17 | Published | AU eRequesting R1 PSS | PSS/20250430 AU eRequesting FHIR IG R1.pdf |
```

Leave `PP:` empty for a project with no proposal on file, and leave the last table cell
empty for a scope statement whose PDF is not in the repository. Projects appear in the
view in the order they appear in the file.

Allowed statuses: `Proposed`, `Submitted`, `Approved`, `Active`, `Inactive`, `Withdrawn`,
and `Published` for PSS rows only.

## File naming

Documents are named `YYYYMMDD <Project> [R<n>].pdf`, where the date is the date on the
document (when the work group approved it), not the date it was emailed to the TSC.
FHIR implementation guides are written as "FHIR IG". PSS and NIB filenames carry the
release as `R1`, `R2` and so on.

## Publishing

The workflow in `.github/workflows/build.yml` builds the site on every push and uploads
it as a build artifact. Deployment to GitHub Pages only runs when the repository variable
`PUBLISH_PAGES` is set to `true`, because **a GitHub Pages site is served publicly even
when the repository is private** — see the deployment notes before turning it on.
