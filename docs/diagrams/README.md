# Editing the system graphics

Made by **DUYTRUYENTHONG**, shared under the repository's MIT license.
These are original documentation assets, not screenshots of candidate accounts.

| Asset | Edit | View |
|---|---|---|
| System overview | `system-overview.svg`: text, shapes and arrows in plain XML | Browser or GitHub image preview |
| Five detailed models | Mermaid blocks in [SYSTEM_MODELS.md](../SYSTEM_MODELS.md) | GitHub Markdown preview or a Mermaid renderer |

The SVG has a fixed 1200 × 880 viewBox, a title/description for assistive tools,
system-font fallbacks and no remote fonts, scripts or image dependencies.
Keep text inside its cards when changing labels. At small widths, open the
standalone SVG; the surrounding Markdown gives the same information as text.

The five Mermaid models cover components/data, roles/routing, Gmail sequence,
parallel browser lanes and outcome recovery. Onboarding QA parsed and rendered
all five with Mermaid 11.12.0 in Chromium and visually inspected the resulting
images; the SVG was parsed as XML, rendered and checked for canvas overflow.
That check does not certify every Markdown host's bundled Mermaid version.
No diagram renderer was added as a runtime dependency of the kit.

When behavior changes, update the matching model and prose in the same commit.
Check labels against the implementation and compatibility evidence. Preserve
the distinction between research and disclosure, Gmail send and delivery,
isolated lanes and shared sessions, and configured capacity and measured speed.
