"""PDF generation helpers with Unicode (Turkish) font support."""

from __future__ import annotations

import io
import logging
import re
from pathlib import Path

from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.frames import Frame

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

_FONT_DIR: Path | None = None
_FONTS_REGISTERED = False


def _resolve_font_dir() -> Path:
    global _FONT_DIR
    if _FONT_DIR is not None:
        return _FONT_DIR

    bundled = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    if (bundled / "DejaVuSans.ttf").is_file():
        _FONT_DIR = bundled
        return bundled

    linux_system = Path("/usr/share/fonts/truetype/dejavu")
    if (linux_system / "DejaVuSans.ttf").is_file():
        _FONT_DIR = linux_system
        return linux_system

    raise AppError(
        "PDF_FONT_UNAVAILABLE",
        "PDF fonts are not available on this server.",
        status_code=503,
    )


def _register_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    font_dir = _resolve_font_dir()
    regular = str((font_dir / "DejaVuSans.ttf").resolve())
    bold = str((font_dir / "DejaVuSans-Bold.ttf").resolve())

    pdfmetrics.registerFont(TTFont("DejaVuSans_00", regular))
    pdfmetrics.registerFont(TTFont("DejaVuSans_10", bold))
    addMapping("DejaVuSans", 0, 0, "DejaVuSans_00")
    addMapping("DejaVuSans", 1, 0, "DejaVuSans_10")
    addMapping("DejaVuSans", 0, 1, "DejaVuSans_00")
    addMapping("DejaVuSans", 1, 1, "DejaVuSans_10")

    _FONTS_REGISTERED = True


def _register_fonts_in_context(context) -> None:
    context.registerFont(
        "DejaVuSans",
        ["dejavusans", "dejavu sans", "DejaVuSans_00", "DejaVuSans_10"],
    )


def _prepare_html_for_pdf(html: str) -> str:
    prepared = re.sub(
        r"font-family:\s*DejaVu Sans[^;]*;",
        "font-family: DejaVuSans, sans-serif;",
        html,
    )
    if "font-family: DejaVuSans" not in prepared:
        if "</head>" in prepared:
            prepared = prepared.replace(
                "</head>",
                "<style>body, body * { font-family: DejaVuSans, sans-serif; }</style></head>",
                1,
            )
        else:
            prepared = (
                "<html><head><style>body, body * { font-family: DejaVuSans, sans-serif; "
                "}</style></head><body>"
                f"{prepared}</body></html>"
            )
    return prepared


def html_to_pdf(html: str) -> bytes:
    try:
        from xhtml2pdf.context import pisaContext
        from xhtml2pdf.default import DEFAULT_CSS
        from xhtml2pdf.document import pisaStory
        from xhtml2pdf.files import cleanFiles
        from xhtml2pdf.util import getBox
        from xhtml2pdf.xhtml2pdf_reportlab import PmlBaseDoc, PmlPageTemplate
    except ImportError as exc:
        raise AppError(
            "PDF_UNAVAILABLE",
            "PDF generation is not available on this server.",
            status_code=503,
        ) from exc

    _register_fonts()
    font_dir = _resolve_font_dir()
    prepared_html = _prepare_html_for_pdf(html)

    context = pisaContext(path=str(font_dir))
    _register_fonts_in_context(context)
    context = pisaStory(
        prepared_html,
        path=str(font_dir),
        encoding="utf-8",
        context=context,
        default_css=DEFAULT_CSS,
    )

    if context.err:
        logger.error("PDF generation failed with %d error(s)", context.err)
        raise AppError("PDF_GENERATION_FAILED", "Could not generate PDF report.", status_code=500)

    out = io.BytesIO()
    x, y, w, h = getBox("1cm 1cm -1cm -1cm", context.pageSize)
    body = PmlPageTemplate(
        id="body",
        frames=[
            Frame(
                x,
                y,
                w,
                h,
                id="body",
                leftPadding=0,
                rightPadding=0,
                bottomPadding=0,
                topPadding=0,
            )
        ],
        pagesize=context.pageSize,
    )
    doc = PmlBaseDoc(
        out,
        pagesize=context.pageSize,
        author=context.meta["author"].strip(),
        subject=context.meta["subject"].strip(),
        keywords=[x.strip() for x in context.meta["keywords"].strip().split(",") if x],
        title=context.meta["title"].strip(),
        showBoundary=0,
        allowSplitting=1,
    )
    doc.addPageTemplates([body, *list(context.templateList.values())])
    doc.build(context.story)
    cleanFiles()

    return out.getvalue()
