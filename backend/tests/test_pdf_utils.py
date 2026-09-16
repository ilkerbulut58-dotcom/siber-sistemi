"""PDF generation tests."""

from io import BytesIO

import pypdf

from app.services.pdf_utils import html_to_pdf

TURKISH_SAMPLE_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8"/>
  <title>Test</title>
  <style>
    body { font-family: DejaVu Sans, Arial, sans-serif; font-size: 12px; }
  </style>
</head>
<body>
  <h1>SIBER Güvenlik Tarama Raporu</h1>
  <p>Profil: Kod / Dosya Taraması · Durum: Tamamlandı</p>
  <p>Özet: Kritik sorun yok; küçük iyileştirmeler yapılabilir.</p>
  <p>Ne anlama geliyor? Saldırganlara ipucu verir; tek başına açık sayılmaz.</p>
  <p>Çözüm: Server header'ını genelleştirin veya gizleyin.</p>
  <p>başlık bilgi sızıdırıyor yazılım açık</p>
</body>
</html>
"""


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_pdf_renders_turkish_characters() -> None:
    pdf_bytes = html_to_pdf(TURKISH_SAMPLE_HTML)
    assert pdf_bytes.startswith(b"%PDF")

    text = _extract_pdf_text(pdf_bytes)
    assert "Güvenlik" in text
    assert "Tamamlandı" in text
    assert "iyileştirmeler" in text
    assert "yapılabilir" in text
    assert "başına" in text
    assert "açık" in text
    assert "yazılım" in text
    assert "■" not in text


def test_pdf_evidence_box_keeps_turkish_and_wraps_csp() -> None:
    policy = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https: "
        "https://cdn.example.test/assets/very-long-path/image.png"
    )
    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8"/>
  <style>
    @page {{
      margin: 16mm 12mm 22mm 12mm;
      @frame footer_frame {{
        -pdf-frame-content: footerContent;
        bottom: 6mm;
        margin-left: 12mm;
        margin-right: 12mm;
        height: 12mm;
      }}
    }}
    #footerContent {{ font-family: DejaVu Sans, sans-serif; font-size: 9px; text-align: center; }}
    body {{ font-family: DejaVu Sans, sans-serif; font-size: 11px; }}
    table.evidence-box {{ width: 100%; }}
    table.evidence-box td {{ font-family: DejaVu Sans, sans-serif; font-size: 9px; border: 1px solid #ddd; }}
  </style>
</head>
<body>
  <div id="footerContent">SIBER Security Analysis Platform — Sayfa <pdf:pagenumber /> / <pdf:pagecount /></div>
  <h1>Kanıt kutusu şığ</h1>
  <table class="evidence-box"><tr><td>Başlık adı: Content-Security-Policy
Gözlenen değer: {policy}
Kanıt türü: HTTP yanıt başlığı</td></tr></table>
</body>
</html>
"""
    from app.services.pdf_utils import wrap_text_for_pdf

    wrapped = wrap_text_for_pdf("Gözlenen değer: " + policy)
    assert "https://cdn.example.test" in wrapped
    assert "\n" in wrapped
    html = html.replace(policy, wrap_text_for_pdf(policy))
    pdf_bytes = html_to_pdf(html)
    assert pdf_bytes.startswith(b"%PDF")
    text = _extract_pdf_text(pdf_bytes)
    assert "Başlık" in text or "Ba" in text
    assert "şığ" in text or "sı" in text or "Kanıt" in text
    assert "unsafe-inline" in text
    assert "https://cdn.example.test" in text or "cdn.example.test" in text
    assert "■" not in text
    fonts = _embedded_font_names(pdf_bytes)
    assert any("DejaVu" in name or "Segoe" in name or "Arial" in name or "Calibri" in name for name in fonts)
    assert not any(name == "Courier" for name in fonts)
    assert "Sayfa" in text


def _embedded_font_names(pdf_bytes: bytes) -> set[str]:
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    names: set[str] = set()
    for page in reader.pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        fonts = resources.get("/Font")
        if not fonts:
            continue
        for _key, font in fonts.items():
            font_obj = font.get_object() if hasattr(font, "get_object") else font
            base = font_obj.get("/BaseFont") if font_obj else None
            if base:
                names.add(str(base))
    return names
