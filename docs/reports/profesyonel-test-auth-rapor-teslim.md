# Profesyonel test öncesi — yetkilendirme ve rapor teslimi (güncel)

## Tamamlanan düzeltmeler

1. **Production DNS zorunluluğu:** `domain_verification_enforced()` prod/staging’de her zaman true; production’da `SKIP_DOMAIN_VERIFICATION` veya `PILOT_RELAX_DOMAIN_VERIFICATION` ile uygulama **başlamaz** (`config.py` model_validator). Pilot relax prod’da etkisiz. Worker `run_scan_job` ve ASM `run_discovery_job` yetkiyi yeniden denetler.
2. **Tüm tarama girişleri:** `ScanService.create` (normal, quick scan, retest, monitoring schedule) merkezi `ScanAuthorizationService`. ASM keşfi create + worker’da aynı servis. Benchmark izole.
3. **Admin DNS muafiyeti:** `users.dns_verification_exempt` + e-posta doğrulanmış + **taramanın org’unda** admin/owner + domain `admin_dns_exempt`. Script: `python -m scripts.assign_admin_dns_exempt <email>`.
4. **Hazır hedefler:** Seed `turbridge.de`, `wolkeshopping.de`; platform API + UI `/dashboard/platform/test-targets`; test kullanıcısı proje sayfasında atanan hedefler ve doğrulama kaynağı etiketleri (TR/DE).
5. **Kapsam / ağ:** `hostname_auth` testleri (suffix saldırısı, alt alan); redirect yeniden kontrolü passive HTTP’de.
6. **Rapor kanıtı:** HTTP header kanıtı (`evidence_type`), planned vs executed scope, örnek PDF TR/DE (`docs/reports/samples/`).

## Örnek PDF

- `docs/reports/samples/sample-scan-report-tr.pdf`
- `docs/reports/samples/sample-scan-report-de.pdf`
- Meta: `*.meta.txt` — **TEST VERİSİ**, canlı değerlendirme değildir.

## Admin ekranı

Platform admin → **Test hedefleri**: `/dashboard/platform/test-targets`

## Test komutu (yerel)

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest `
  tests/test_scan_target_authorization.py `
  tests/test_production_domain_config.py `
  tests/test_hostname_auth.py `
  tests/test_generate_sample_report_pdf.py `
  tests/test_pilot_relax_domain.py `
  tests/test_scans.py `
  tests/test_reports.py -q
```

Son koşu: **33 passed** (authorization + config + hostname + PDF + pilot + scans + reports).

## Migration

`020_scan_target_auth_and_reports.py` — predefined targets, assignments, `dns_verification_exempt`, `authorization_source`, eski `pilot_relax`/`test_skip` domain geçersizliği.

## Canlı doğrulama (deploy sonrası operatör)

1. Health: `skip_domain_verification` false (API health payload).
2. `alembic current` → `020` revision.
3. `docker compose exec api python -m scripts.assign_admin_dns_exempt ilkerbulut83@hotmail.com` (koşullar sağlanırsa).
4. Yetki smoke: doğrulanmamış domain ile scan → `DOMAIN_NOT_VERIFIED` (**aktif tarama başlatmadan** API ile).
