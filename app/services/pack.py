from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.schemas import Analysis

ROOT = Path(__file__).parent.parent
env = Environment(
    loader=FileSystemLoader(ROOT / "templates"), autoescape=select_autoescape(["html", "xml"])
)


def render_pack(analysis: Analysis, include_notes: bool = False) -> str:
    return env.get_template("evidence_pack.html.j2").render(
        analysis=analysis, include_notes=include_notes
    )


def pdf_pack(analysis: Analysis, include_notes: bool = False) -> bytes:
    # WeasyPrint depends on system Pango/GObject libraries, so keep the import
    # lazy: API health and HTML preview remain available when PDF support has
    # not yet been installed on a deployment host.
    from weasyprint import HTML

    return HTML(
        string=render_pack(analysis, include_notes), base_url=str(ROOT / "static")
    ).write_pdf()
