# Profesyonel test — rapor/yayın kapanışı (2026-09-16)

Yerel uygulama düzeltmeleri bu commit ile. Canlı doğrulama ayrı satırda.

## Kök neden ve düzeltme

| Sorun | Kök neden | Düzeltme |
| --- | --- | --- |
| PDF Türkçe kare, CSP kesilme, kural taşması, sayfa no yok | `pre` + Courier; xhtml2pdf desteklemediği CSS; özel body şablonu altbilgiyi eziyordu; `pagecount` için `multiBuild` yoktu | DejaVu/sistem Unicode font; Courier eşlemesi kaldırıldı; kanıt tablosu + satır sarma; `@page` şablonu + `multiBuild` |
| X-Powered-By çözümünde "—" | `contextual_remediation` `tool_evidence` okumuyordu | Ortak `normalize_finding_evidence`; UI API ve çözüm aynı kayıt |
| CSP/Cache İngilizce genel metin | `generic.csp-*` katalogda yok; yer tutucu risk; ZAP başlığı missing-header’a kayıyordu | Katalog TR/DE; başlık/kural anahtarı; XSS iddiası yok; `*` yoksa yazılmaz; s-maxage sızıntı sayılmaz |
| URL=2, 8→7 yok, ZAP pasif/aktif | Raporda `unique_urls_scanned_sum` (motor toplamı) benzersiz sanılıyordu; `raw_finding_sources` legacy’de yok; kontrol metni motor yeteneği | Raporda benzersiz URL uydurulmaz; ham kaynak bulgulardan; ZAP modu kaydedilmediyse belirtilir |
| Export No such file | PDF container `/tmp`, SFTP host `/tmp` | `docker cp` host `/var/tmp`; UUID/locale doğrulama; aşama log; temizlik; PDF imza kontrolü |
| Health git doğru, sürüm rc8 | Eski `.env` `set -a` ile `APP_VERSION` shell’de kalıyor; compose shell’i tercih ediyor | `.env` yazıldıktan sonra `export APP_VERSION`; image build-arg; worker/frontend ayrı beklenir |

## Testler (yerel)

```text
py -m pytest          299 passed, 7 warnings
ruff (değişen dosyalar) All checks passed
frontend typecheck    OK
vitest evidence-masker 4 passed
```

Görsel: `docs/reports/samples/sample-scan-report-tr.pdf` ve `-de.pdf` aynı motor. Kanıt kutusunda Başlık/şığ, CSP tam ve sarılı, Sayfa n / N, Courier yok.

## Yayın

Etiket ve CI/deploy bu dosyada commit sonrası doldurulur; sohbet teslim tablosu günceldir.
