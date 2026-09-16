# Profesyonel test — kanıt/rapor/profil teslimi (2026-09-16)

## Commit ve CI

| Öğe | Değer |
| --- | --- |
| RC9 kanıt/SPF | `d1608cb` … `520a376` |
| CI düzeltme (ruff) | `7c7355d` |
| **Release (deploy hedefi)** | `7c7355d` + etiket `v0.9.0-rc9-evidence-profile-4` |
| CI #153 | https://github.com/ilkerbulut58-dotcom/siber-sistemi/actions/runs/35083923384 — **success** |
| CI #152 (`bed197b`) | backend **ruff failure** (düzeltildi `7c7355d` ile) |

**Frontend CI kök nedeni:** `frontend/src/lib/i18n/types.ts` içinde sözlükte olan `platform.testTargetsTitle` / `project.verificationDnsVerified` (ve site profili SPF etiketleri) tip tanımında yoktu → `tsc --noEmit` kırılıyordu. **Düzeltme:** eksik anahtarlar `types.ts`, `tr.ts`, `de.ts` ile hizalandı; yerelde `npm run typecheck` geçti.

**Backend CI:** CI #153 `backend` job’da tam pytest geçti. Yerelde `py -m pytest` → **290 passed, 0 failed** (`test_platform_admin_dns_policy`, commit `520a376`).

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
py -m pytest (tam)         — 290 passed, 0 failed
test_platform_admin_skips_domain_verification → test_platform_admin_dns_policy (520a376)
```

## Production dağıtım

Bu oturumda `DEPLOY_SSH_PASSWORD` ortamda yok → **deploy çalıştırılmadı**. Onaylı komut:

```powershell
$env:DEPLOY_CONFIRM='production-pilot'
$env:RELEASE_TAG='v0.9.0-rc9-evidence-profile-4'
$env:APP_VERSION='0.9.0-rc9-evidence-profile'
# DEPLOY_SSH_PASSWORD: Cursor Agent ortam değişkeni veya bu terminal oturumunda (sohbete yazmayın)
.\scripts\rc9-production-verify.ps1
```

Sonra: health `git_commit=7c7355d`, `scan-a6426ea8-report-tr.pdf`, `ssh-prod-dns-reject-smoke.cjs` → `DNS_REJECT_SMOKE_OK`.

## Yetkilendirme

| Senaryo | Durum |
| --- | --- |
| Doğrulanmamış hedef → tarama | Yerel: `test_unverified_domain_rejected` → 400 `DOMAIN_NOT_VERIFIED` |
| Atanmış test hedefi (turbridge.de) DNS’siz | `test_assigned_predefined_target_without_dns` |
| Admin DNS exempt (ilker) | `test_admin_dns_exempt_user` |
| Canlı normal kullanıcı DNS reddi | **Doğrulanamadı** — `DEPLOY_SSH_PASSWORD` agent oturumunda yok; yerel API: `test_unverified_domain_rejected`, `test_platform_admin_cannot_scan_unverified_domain` |

## Kalan sınırlamalar

- `a6426ea8` PDF’inde DB’de hiç kaydedilmemiş alanlar (eski tarama `59f266d8` ile karşılaştırma) geriye dönük doldurulmaz; yalnız mevcut `tool_evidence` gösterilir.
- Production deploy + `a6426ea8` PDF + canlı DNS smoke: **tek eksik adım** agent oturumunda `DEPLOY_SSH_PASSWORD` (User/Machine/Agent env).

**Profesyonel kullanım testine hazırlık:** Kod + yerel testler tamam; **production’da rc9 deploy, CI yeşil kanıtı ve canlı DNS red smoke** tamamlanmadan “canlı hazır” denmemeli.
