# HL7 AU Project Registry

A simple registry of HL7 Australia projects: each project proposal (PP) with its child
project scope statements (PSS), rendered as a single HTML page with the source PDFs.

## Contents

| Path | What it holds |
| --- | --- |
| `registry.md` | The source of truth — projects, scope statements, statuses and document links |
| `build.py` | Generates `index.html` from `registry.md` (standard library only) |
| `tools/` | The scripts behind the submission workflow |
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

## Submitting to the TSC

Work groups submit an approved document to the AU TSC by opening an issue:

| Form | What it adds |
| --- | --- |
| [**Submit a project proposal**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=pp-submission.yml) | A project, with the proposal PDF in `PP/` |
| [**Submit a project scope statement**](https://github.com/hl7au/hl7au-projects-registry/issues/new?template=pss-submission.yml) | A scope statement under a project, with the PSS PDF in `PSS/` |

Each form links the blank `.docx` template to write on, and asks for the
project, the work group, the work group's approval date and the approved PDF
dragged into the form; the scope statement form also asks for the PSS title and
the release. The attachment must be a PDF — a `.docx` is rejected — and those
answers are what the file name is built from, so the submitter's own file name
does not matter.

Blank issues are turned off, so every issue starts from a form and a submission
always arrives with the metadata the registry needs; the fields themselves are
required, so a half-filled form cannot be sent. Anything that is not a
submission goes through the **Something else** form, which the workflow ignores.

`.github/workflows/submission.yml` then turns the issue into a pull request — it
files the PDF under the naming convention, adds the entry to `registry.md` with
status `Submitted`, and checks that the registry still builds. The TSC reviews
and merges the pull request; changing the status later is an ordinary edit to
`registry.md`.

Project IDs are allocated by the workflow: a new project gets the next `AU####`
after the highest already in the registry. A proposal for a project that is
already listed without one is attached to that entry instead, leaving its status
and submitted date alone; a project that already has a proposal is refused.
Submitting a scope statement for a project that is not listed yet creates the
project entry with no proposal, and the pull request says so.

When the submission is malformed — a release that is not `R<n>`, a date that is
not `YYYY-MM-DD`, an attachment that is not a PDF — the workflow comments the
error on the issue. The submitter edits the issue and a maintainer re-runs the
workflow from the Actions tab with the issue number.

`tools/pp_from_issue.py` and `tools/pss_from_issue.py` do the work, sharing
`tools/registry_issue.py`, and run locally too:

```bash
python tools/pss_from_issue.py --body issue.md --summary pr-body.md
```

The workflow can only open the pull request while **Settings > Actions > General >
Allow GitHub Actions to create and approve pull requests** stays on.

GitHub does not run `pull_request` workflows for a pull request opened by a
workflow, so `build.yml` does not fire on these. The submission workflow builds
the registry itself before pushing and reports the result on the pull request as
a `registry build` commit status; a later push to the branch by a reviewer is an
ordinary push and does trigger CI.

## File naming

Documents are named `YYYYMMDD <Project> [R<n>].pdf`, where the date is the date on the
document (when the work group approved it), not the date it was emailed to the TSC.
FHIR implementation guides are written as "FHIR IG". PSS and NIB filenames carry the
release as `R1`, `R2` and so on.

## View options

| URL | Effect |
| --- | --- |
| `index.html` | Content centred in the window (the default) |
| `index.html?align=left` | Content pinned to the left edge — use this when embedding in a page that does its own centring |

## Publishing

The workflow in `.github/workflows/build.yml` builds the site on every push and uploads
it as a build artifact. Deployment to GitHub Pages only runs when the repository variable
`PUBLISH_PAGES` is set to `true`, because **a GitHub Pages site is served publicly even
when the repository is private** — see the deployment notes before turning it on.
