"""PDF generation tests."""

from io import BytesIO

import pypdf
import pytest

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
