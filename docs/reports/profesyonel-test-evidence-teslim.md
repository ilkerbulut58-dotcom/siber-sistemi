# Profesyonel test — kanıt/rapor/profil teslimi (2026-09-16)

## Commit ve CI

| Öğe | Değer |
| --- | --- |
| Ana düzeltme | `d1608cb` — correlated `tool_evidence`, SPF, kapsam sayımı |
| Takip | `e8bbaa6` (ruff), `520a376` (pilot test + bu teslim) |
| Deploy etiketi | `v0.9.0-rc9-evidence-profile-3` → `520a376` |
| Actions | https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions (son push `520a376`) |

**Frontend CI kök nedeni:** `frontend/src/lib/i18n/types.ts` içinde sözlükte olan `platform.testTargetsTitle` / `project.verificationDnsVerified` (ve site profili SPF etiketleri) tip tanımında yoktu → `tsc --noEmit` kırılıyordu. **Düzeltme:** eksik anahtarlar `types.ts`, `tr.ts`, `de.ts` ile hizalandı; yerelde `npm run typecheck` geçti.

**Backend CI:** Paylaşılan ekrandaki frontend tip hatası dışında, CI ortamında `ENVIRONMENT=development` olduğu için `QuotaService.requires_domain_verification` testleri geçer. Tam pytest yerelde `289 passed, 1 failed` (`test_platform_admin_skips_domain_verification` — production `Settings` ile bilinçli DNS zorunluluğu); CI ile uyumlu.

## Kanıt kaybı

| Aşama | Bulgu |
| --- | --- |
| Kök | Korelasyon sonrası kanıt `evidence.tool_evidence.{tls_check,passive_http,zap}` altında; rapor `format_evidence_for_report` yalnız düz alan okuyordu |
| Düzeltme | `finding_evidence.flatten_finding_evidence`, enrichment + korelasyonda üst seviye promosyon |
| Test | `tests/test_evidence_report_regression.py` (3), `tests/test_site_profile_spf.py` (4) |

**Örnek tarama `a6426ea8-d574-41ea-92fc-d37157af71d3`:** DB’deki mevcut kanıtla PDF yenileme için deploy sonrası:

`DEPLOY_SSH_PASSWORD=... node scripts/ssh-export-scan-report-pdf.cjs a6426ea8-d574-41ea-92fc-d37157af71d3 tr`

Çıktı: `docs/reports/samples/scan-a6426ea8-report-tr.pdf` (deploy edilmeden üretilemez).

Sentetik örnekler (yerel test fixture): `docs/reports/samples/sample-scan-report-tr.pdf`, `sample-scan-report-de.pdf`.

## SPF tutarsızlığı

**Neden:** Parçalı/quoted TXT birleştirilmeden SPF satırı `v=spf1` ile eşleşmiyordu; UI “Yok” gösteriyordu. **Düzeltme:** `dns_collector` TXT `strings` birleştirme; `site_intelligence._parse_email_security` + `spf_status` (`found` / `not_found` / `invalid_multiple` / sorgu hatası ayrımı UI’da).

## URL / bulgu sayımı

- Motor satırları: passive 3 + ZAP 5 = **8 ham kaynak**; birleştirme sonrası **7 benzersiz bulgu** (`raw_finding_sources` + `finding_dedup` metni).
- URL: ZAP=1 ve Nuclei=1 **benzersiz toplam 2 değil** — motor başına ölçüm; raporda “Motor başına (benzersiz toplam değil): zap=1, nuclei=1”.

## Yerel testler

```text
npm run typecheck          — OK
npm run lint               — OK (yalnız uyarılar)
py -m pytest (tam)         — 289 passed, 1 failed (production DNS test; CI development)
py -m pytest tests/test_evidence_report_regression.py tests/test_site_profile_spf.py tests/test_scan_target_authorization.py tests/test_generate_sample_report_pdf.py — 28 passed
```

## Production dağıtım

Bu oturumda `DEPLOY_SSH_PASSWORD` ortamda yok → **deploy çalıştırılmadı**. Onaylı komut:

```powershell
$env:DEPLOY_CONFIRM='production-pilot'
$env:RELEASE_TAG='v0.9.0-rc9-evidence-profile-3'
$env:APP_VERSION='0.9.0-rc9-evidence-profile'
$env:DEPLOY_SSH_PASSWORD='…'
node scripts/deploy-pilot-production.cjs
```

Sonra: health `git_commit=520a376`, `ssh-export-scan-report-pdf.cjs` ile `a6426ea8` PDF.

## Yetkilendirme

| Senaryo | Durum |
| --- | --- |
| Doğrulanmamış hedef → tarama | Yerel: `test_unverified_domain_rejected` → 400 `DOMAIN_NOT_VERIFIED` |
| Atanmış test hedefi (turbridge.de) DNS’siz | `test_assigned_predefined_target_without_dns` |
| Admin DNS exempt (ilker) | `test_admin_dns_exempt_user` |
| Canlı normal kullanıcı DNS reddi | **Bu oturumda canlı API smoke yapılmadı** (parola/token gerekir) |

## Kalan sınırlamalar

- `a6426ea8` PDF’inde DB’de hiç kaydedilmemiş alanlar (eski tarama `59f266d8` ile karşılaştırma) geriye dönük doldurulmaz; yalnız mevcut `tool_evidence` gösterilir.
- GitHub Actions sonucu bu makinede `gh` yok; Actions web UI’dan #150 yeşil doğrulanmalı.
- Production deploy ve canlı yetki negatif testi operatör adımı.

**Profesyonel kullanım testine hazırlık:** Kod + yerel testler tamam; **production’da rc9 deploy, CI yeşil kanıtı ve canlı DNS red smoke** tamamlanmadan “canlı hazır” denmemeli.
