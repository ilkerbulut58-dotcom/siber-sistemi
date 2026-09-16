"""PDF generation helpers with Unicode (Turkish/German) font support."""

from __future__ import annotations

import io
import logging
import os
import re
from pathlib import Path

from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.frames import Frame

from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

_FONT_DIR: Path | None = None
_FONT_REGULAR: Path | None = None
_FONT_BOLD: Path | None = None
_FONTS_REGISTERED = False

_WRAP_WIDTH = 88


def wrap_text_for_pdf(text: str, width: int = _WRAP_WIDTH) -> str:
    """Insert display line breaks without dropping or substituting characters."""
    if not text:
        return text
    lines: list[str] = []
    for raw_line in text.split("\n"):
        lines.extend(_wrap_line(raw_line, width))
    return "\n".join(lines)


def _wrap_line(line: str, width: int) -> list[str]:
    if len(line) <= width:
        return [line]
    parts: list[str] = []
    remaining = line
    while len(remaining) > width:
        window = remaining[: width + 1]
        break_at = -1
        for sep in (";", ",", " ", "/", "?", "&", "="):
            idx = window.rfind(sep)
            if idx >= width // 3:
                break_at = idx + 1
                break
        if break_at < 0:
            break_at = width
        parts.append(remaining[:break_at])
        remaining = remaining[break_at:]
    if remaining:
        parts.append(remaining)
    return parts or [line]


def _resolve_font_files() -> tuple[Path, Path]:
    global _FONT_DIR, _FONT_REGULAR, _FONT_BOLD
    if _FONT_REGULAR is not None and _FONT_BOLD is not None:
        assert _FONT_DIR is not None
        return _FONT_REGULAR, _FONT_BOLD

    candidates: list[tuple[Path, Path]] = []
    bundled = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    candidates.append((bundled / "DejaVuSans.ttf", bundled / "DejaVuSans-Bold.ttf"))
    linux_system = Path("/usr/share/fonts/truetype/dejavu")
    candidates.append((linux_system / "DejaVuSans.ttf", linux_system / "DejaVuSans-Bold.ttf"))
    windir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    candidates.extend(
        [
            (windir / "DejaVuSans.ttf", windir / "DejaVuSans-Bold.ttf"),
            (windir / "segoeui.ttf", windir / "segoeuib.ttf"),
            (windir / "arial.ttf", windir / "arialbd.ttf"),
            (windir / "calibri.ttf", windir / "calibrib.ttf"),
        ]
    )
    for regular, bold in candidates:
        if regular.is_file() and bold.is_file():
            _FONT_REGULAR = regular
            _FONT_BOLD = bold
            _FONT_DIR = regular.parent
            return regular, bold

    raise AppError(
        "PDF_FONT_UNAVAILABLE",
        "PDF fonts are not available on this server.",
        status_code=503,
    )


def _resolve_font_dir() -> Path:
    regular, _bold = _resolve_font_files()
    return regular.parent


def _register_fonts() -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return

    regular, bold = _resolve_font_files()
    pdfmetrics.registerFont(TTFont("DejaVuSans_00", str(regular.resolve())))
    pdfmetrics.registerFont(TTFont("DejaVuSans_10", str(bold.resolve())))
    addMapping("DejaVuSans", 0, 0, "DejaVuSans_00")
    addMapping("DejaVuSans", 1, 0, "DejaVuSans_10")
    addMapping("DejaVuSans", 0, 1, "DejaVuSans_00")
    addMapping("DejaVuSans", 1, 1, "DejaVuSans_10")
    addMapping("Courier", 0, 0, "DejaVuSans_00")
    addMapping("Courier", 1, 0, "DejaVuSans_10")
    addMapping("Courier", 0, 1, "DejaVuSans_00")
    addMapping("Courier", 1, 1, "DejaVuSans_10")

    _FONTS_REGISTERED = True


def _register_fonts_in_context(context) -> None:
    aliases = [
        "dejavusans",
        "dejavu sans",
        "DejaVuSans_00",
        "DejaVuSans_10",
        "courier",
        "Courier",
    ]
    context.registerFont("DejaVuSans", aliases)
    context.registerFont("Courier", aliases)


def _pdf_default_css() -> str:
    from xhtml2pdf.default import DEFAULT_CSS

    return (
        DEFAULT_CSS.replace("Courier", "DejaVuSans")
        .replace("courier", "DejaVuSans")
        .replace("monospace", "DejaVuSans")
    )


def _prepare_html_for_pdf(html: str) -> str:
    prepared = re.sub(
        r"font-family:\s*DejaVu Sans[^;]*;",
        "font-family: DejaVuSans, sans-serif;",
        html,
    )
    prepared = re.sub(
        r"font-family:\s*Courier[^;]*;",
        "font-family: DejaVuSans, sans-serif;",
        prepared,
        flags=re.IGNORECASE,
    )
    override = (
        "<style>html, body, body *, pre, code, table, td, th, #footerContent "
        "{ font-family: DejaVuSans, sans-serif; }</style>"
    )
    if "</head>" in prepared:
        prepared = prepared.replace("</head>", f"{override}</head>", 1)
    else:
        prepared = f"<html><head>{override}</head><body>{prepared}</body></html>"
    return prepared


def html_to_pdf(html: str) -> bytes:
    try:
        from xhtml2pdf.context import pisaContext
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
        default_css=_pdf_default_css(),
    )

    if context.err:
        logger.error("PDF generation failed with %d error(s)", context.err)
        raise AppError("PDF_GENERATION_FAILED", "Could not generate PDF report.", status_code=500)

    out = io.BytesIO()
    if "body" in context.templateList:
        body = context.templateList["body"]
        del context.templateList["body"]
    else:
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
    if context.multiBuild:
        doc.multiBuild(context.story)
    else:
        doc.build(context.story)
    cleanFiles()

    return out.getvalue()
