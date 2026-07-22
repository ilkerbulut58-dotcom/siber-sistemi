# SIBER — Security Analysis Platform

Yetkilendirilmiş web uygulamaları ve API'ler için yapay zekâ destekli güvenlik analiz SaaS platformu.

**Production:** [https://siber.cloudnira.com](https://siber.cloudnira.com)

---

## Mevcut Özellikler

### Kimlik ve Erişim (Faz 2)
- Kayıt, giriş, JWT access/refresh token (otomatik yenileme)
- Organizasyonlar, roller (owner / admin / security_analyst / developer / viewer)
- Audit log

### Proje ve Domain (Faz 3–4)
- Proje oluşturma (`production` / `staging` ortamı)
- Domain ekleme ve sahiplik doğrulama (DNS TXT, `.well-known`, meta etiket)
- **Test modu:** `SKIP_DOMAIN_VERIFICATION=true` ile DNS doğrulama atlanır

### Tarama (Faz 4–7)
- **Hızlı Tarama** (`/dashboard/scan`) — URL gir, domain/proje otomatik oluşur
- Üç tarama profili:

| Profil | Ad | Ne yapar | Ortam |
|--------|-----|----------|-------|
| `safe` | Güvenli Tarama | Pasif HTTP/TLS + ZAP pasif + Nuclei (passive) | Production OK |
| `deep` | Derin Tarama | Safe + yüzey taraması + ZAP spider (pasif) + Nuclei | Staging (test modunda serbest) |
| `code` | Kod / Dosya Taraması | Pasif HTTP + hassas dosya + kaynak sızıntı desenleri | Staging (test modunda serbest) |

- Tüm profiller **pasif ve güvenli** — form göndermez, brute-force yapmaz
- Deep/code için Quick Scan otomatik **staging** projesi kullanır
- Tarama durumları: `queued` → `validating` → `running` → `parsing` → `completed`
- **Performans ve güvenilirlik:** tarayıcılar paralel çalışır; profil başına sert zaman aşımı vardır. Takılı kalan taramalar otomatik `failed` olarak işaretlenir.

| Profil | Tahmini süre | Genel zaman aşımı |
|--------|--------------|-------------------|
| `safe` | ~1–2 dk | 120 sn |
| `deep` | ~2–4 dk | 240 sn |
| `code` | ~30–90 sn | 90 sn |

### Tarama Sonuç Dashboard (UX)
- Modern SaaS görünümü: güvenlik skoru, risk dağılımı, kaynak araç özeti
- Güvenlik başlıkları grid'i, risk trend grafiği, AI özet kartı
- Bulgu vurguları + filtreli tam liste paneli
- Canlı durum takibi (polling); token otomatik yenileme

### Bulgular (Faz 5–7A)
- Pasif HTTP güvenlik başlıkları, TLS sertifika kontrolü, cookie bayrakları
- HTTP→HTTPS yönlendirme, `X-Powered-By` ifşası
- Bulgu normalizasyonu, deduplication (fingerprint hash)
- **Türkçe bulgu kataloğu** + Plesk odaklı çözüm adımları (`config_file_paths`, `config_snippet`)
- Bulgu geçmişi, durum güncelleme, yeniden tarama (retest)
- AI özet kartı (kural tabanlı Türkçe özet — gerçek LLM Faz 8)

### Raporlama (Faz 7B)
- Tarama sonuçları için **HTML**, **PDF** ve **JSON** rapor indirme
- Türkçe rapor şablonu, önem derecesi özeti

### ZAP Pasif Analiz (Faz 7C)
- OWASP ZAP daemon — yalnızca **pasif** kurallar (aktif saldırı/ascan yok)
- **Safe:** hedef URL pasif analiz
- **Deep:** sınırlı spider + pasif analiz (max 8 alt sayfa, aynı site)
- ZAP erişilemezse veya zaman aşımına uğrarsa tarama **atlanır** — diğer tarayıcılar sonucu tamamlar

### Analiz Motorları (Faz 7D)
Tarama sonuçları ham bulgu listesi olarak kalmaz; platform bunları analiz edip önceliklendirir:

| Motor | Görev |
|-------|-------|
| **Correlation Engine** | Aynı güvenlik açığını farklı araçlardan (passive_http, ZAP, Nuclei vb.) eşleştirir → tek bulgu, çoklu kaynak |
| **Verification Engine** | Yalnızca **pasif/güvenli** doğrulama (header GET, TLS, yönlendirme) — aktif saldırı yok |
| **Risk Engine** | Severity, CVSS, confidence, exposure ve scanner güvenilirliğine göre **1–100 risk puanı** |

Bulgu alanları: `correlation_key`, `risk_score`, `cvss_score`, `source_tools`, `verification_status`, `confidence` (Low/Medium/High).

### Sürekli İzleme (Faz 7D)
- Zamanlanmış taramalar (`scan_schedules`) — Celery Beat her 5 dk kontrol eder
- Tarama sonrası **delta analizi**: yeni / kapanan / tekrar açılan bulgular
- `monitoring_events` tablosu ve REST API: `/organizations/{orgId}/monitoring/...`

### AI Analizi (Faz 8)
- **Gerçek LLM entegrasyonu** (OpenAI uyumlu API) — tarama tamamlandıktan sonra Celery ile arka planda çalışır
- Her bulgu için Türkçe **AI özeti**, **düzeltme önerisi** ve **güven etiketi** (`verified` / `unverified` / `likely_false_positive`)
- Hassas veri maskeleme (JWT, API key, Cookie/Authorization) — güvenlik politikasına uygun
- AI hatası taramayı **engellemez**; kural tabanlı yedek özet anında uygulanır

### Faz 9 — Attack Surface ve Mobil Uygulama Güvenliği
- Domain'den başlayarak **pasif saldırı yüzeyi analizi** (yalnızca doğrulanmış hedefler)
- Alt domain keşfi (CT log + sınırlı DNS), DNS kayıtları, TLS envanteri
- HTTP güvenlik başlıkları, teknoloji tespiti (web server, CMS, framework)
- CDN/WAF tespiti, IP ve subdomain varlık envanteri
- Dashboard'da görsel **Attack Surface** görünümü + Risk Engine entegrasyonu
- Android APK için yetkili, yalnızca statik analiz: manifest, izinler, exported component, network security ve secret sinyalleri
- Özel APK depolama, SHA-256 deduplikasyonu, ZIP bomb/path traversal koruması ve analiz sonrası artifact temizliği
- Mobil analiz ayrı, ağ erişimi kapalı Celery worker’da CPU/RAM/PID/zaman limitleriyle çalışır
- Mobil dashboard, Finding Drawer ve HTML/PDF/JSON raporları
- Genişletilebilir varlık tipleri: `api`, `mobile`, `service`

### Altyapı
- Docker Compose (API, Frontend, PostgreSQL, Redis, Celery worker + **Beat** + izole mobile worker)
- Nuclei v3.3.7 + şablonlar API/worker imajında
- Plesk reverse proxy: `/api/v1/*` → API, `/` → Frontend

---

## Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind, shadcn/ui |
| Backend | Python 3.12, FastAPI, SQLAlchemy (async), Alembic |
| Queue | Celery 5 + Redis 7 |
| Database | PostgreSQL 16 |
| Scanners | passive_http, surface_crawl, exposed_paths, secret_patterns, Nuclei, ZAP (pasif) |
| Infra | Docker, Docker Compose, Plesk/Nginx |

---

## Production Deploy

Sunucu: `root@87.106.10.169` — uygulama `/opt/siber` altında Docker Compose ile çalışır.

```powershell
# Windows — SSH şifresini ortam değişkeni olarak verin
$env:DEPLOY_SSH_PASSWORD = "..."
node scripts/deploy-full.cjs
```

Deploy scripti otomatik olarak:
- Docker imajlarını build eder (API + Frontend + Nuclei)
- PostgreSQL migration'ları çalıştırır
- Admin kullanıcısı oluşturur/günceller
- Plesk proxy ayarlarını yapılandırır
- `SKIP_DOMAIN_VERIFICATION=true` test modunu etkinleştirir

### Servisler (Production)

| Servis | Port | Açıklama |
|--------|------|----------|
| API | `127.0.0.1:8010` | FastAPI |
| Frontend | `127.0.0.1:3011` | Next.js standalone |
| Worker | — | Celery scan worker + Beat (monitoring kuyruğu) |
| ZAP | internal | OWASP ZAP daemon (pasif analiz) |
| PostgreSQL | internal | Kalıcı volume |
| Redis | internal | Celery broker |

### Varsayılan Admin

| Alan | Değer |
|------|-------|
| E-posta | `admin@admin.com` |
| Şifre | `admin` |

---

## Hızlı Başlangıç (Yerel)

### Gereksinimler

- Docker & Docker Compose
- Node.js 20+ (yerel frontend)
- Python 3.12+ (yerel backend)

### Docker ile

```bash
cp .env.example .env
docker compose up -d

# Celery worker (opsiyonel — taramalar background task ile de çalışır)
docker compose --profile workers up -d worker
```

| Servis | URL |
|--------|-----|
| Frontend | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health | http://localhost:8000/api/v1/health |

### Yerel Geliştirme (Docker olmadan)

**Backend:**

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

**Test modu (DNS atla):**

```powershell
$env:SKIP_DOMAIN_VERIFICATION = "true"
```

---

## Kullanım

1. [https://siber.cloudnira.com/dashboard/scan](https://siber.cloudnira.com/dashboard/scan) adresine gidin
2. Hedef URL girin (ör. `https://siteniz.com`)
3. Tarama profilini seçin (Güvenli / Derin / Kod)
4. Yetki onayını işaretleyip **Taramayı Başlat**
5. Sonuç sayfasında bulguları inceleyin; tamamlanan taramalarda **HTML/PDF/JSON rapor** indirin

---

## Test

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest

# Canlı URL ile scanner testi (deploy öncesi)
$env:PYTHONPATH = "."
.\.venv\Scripts\python.exe scripts\test_live_scan.py https://ornek.com deep

# Production API testi (deploy sonrası)
.\.venv\Scripts\python.exe scripts\test_production_scans.py https://ornek.com
```

```bash
cd frontend && npm test
```

---

## Proje Yapısı

```
├── backend/
│   ├── app/
│   │   ├── analysis/        # Correlation, verification, risk, pipeline
│   │   ├── api/v1/          # REST route handlers (+ monitoring)
│   │   ├── core/            # Config, DB, Redis, güvenlik
│   │   ├── data/            # Türkçe bulgu kataloğu
│   │   ├── models/          # SQLAlchemy ORM
│   │   ├── schemas/         # Pydantic modeller
│   │   ├── scanners/        # passive_http, nuclei, exposed_paths, surface_crawl, ...
│   │   ├── services/        # İş mantığı
│   │   ├── tasks/           # Celery görevleri
│   │   └── templates/       # HTML rapor şablonları
│   ├── alembic/             # DB migration'ları
│   ├── scripts/             # Admin oluşturma, canlı test scriptleri
│   └── tests/
├── frontend/
│   └── src/
│       ├── app/dashboard/   # Dashboard, scan, scan detail
│       ├── components/      # UI bileşenleri
│       └── lib/             # API client, i18n-tr
├── docs/                    # Mimari, tehdit modeli, güvenlik politikası
├── scripts/deploy-full.cjs  # Production deploy
├── docker-compose.yml       # Yerel geliştirme
└── docker-compose.prod.yml  # Production
```

---

## Geliştirme Fazları

| Faz | Durum | Açıklama |
|-----|-------|----------|
| 1 | ✅ | Altyapı, Docker, health checks |
| 2 | ✅ | Auth, organizasyon, roller, dashboard UI |
| 3 | ✅ | Proje ve domain doğrulama |
| 4 | ✅ | Scan kuyruğu, profiller, dashboard |
| 5 | ✅ | Bulgular, pasif HTTP/TLS, Nuclei |
| 6 | ✅ | Bulgu geçmişi, AI özet stub, retest, test modu |
| 7A | ✅ | Türkçe bulgular, Plesk çözüm rehberi, Safe+ pasif |
| 7A+ | ✅ | Deep/Code scan düzeltmesi, staging proje, Nuclei Docker |
| 7B | ✅ | HTML/PDF/JSON raporlar, Celery worker |
| 7C | ✅ | OWASP ZAP pasif tarama (Safe + Deep, aktif saldırı yok) |
| 7D | ✅ | Correlation + Verification + Risk motorları, sürekli izleme |
| 8 | ✅ | Gerçek LLM AI analizi (OpenAI uyumlu), AI özet kartı |
| 9 | ✅ | Attack Surface Management (ASM) — pasif keşif, varlık envanteri |
| 10 | 🔜 | Semgrep kod taraması, billing |

---

## Ortam Değişkenleri

| Değişken | Açıklama | Varsayılan |
|----------|----------|------------|
| `DATABASE_URL` | PostgreSQL bağlantısı | — |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `SECRET_KEY` | JWT imzalama anahtarı | — |
| `SKIP_DOMAIN_VERIFICATION` | DNS doğrulamayı atla (test) | `false` |
| `USE_CELERY_FOR_SCANS` | Taramaları Celery worker'a gönder | `false` (prod: `true`) |
| `ZAP_API_URL` | OWASP ZAP daemon API | `http://localhost:8080` (prod: `http://zap:8080`) |
| `ZAP_ENABLED` | ZAP pasif taramayı etkinleştir | `true` |
| `SCAN_TIMEOUT_SAFE_SECONDS` | Safe profil genel zaman aşımı | `120` |
| `SCAN_TIMEOUT_DEEP_SECONDS` | Deep profil genel zaman aşımı | `240` |
| `SCAN_TIMEOUT_CODE_SECONDS` | Code profil genel zaman aşımı | `90` |
| `ZAP_PASSIVE_WAIT_SECONDS` | ZAP pasif kuyruk bekleme süresi | `45` |
| `ZAP_SPIDER_WAIT_SECONDS` | ZAP spider bekleme süresi (deep) | `60` |
| `NUCLEI_TIMEOUT_SECONDS` | Nuclei subprocess zaman aşımı | `90` |
| `SCAN_STALE_MINUTES` | Takılı taramaları failed işaretle | `30` |
| `AI_ENABLED` | LLM bulgu analizini etkinleştir | `false` |
| `OPENAI_API_KEY` | OpenAI (veya uyumlu) API anahtarı | — |
| `AI_MODEL` | LLM model adı | `gpt-4o-mini` |
| `AI_BASE_URL` | OpenAI uyumlu API URL | `https://api.openai.com/v1` |
| `CORS_ORIGINS` | İzin verilen origin'ler | `http://localhost:3000` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token süresi | `15` (prod: `480`) |

---

## Güvenlik

Bu platform yalnızca domain sahipliği doğrulanmış (veya test modunda yetkilendirilmiş) hedeflerde çalışır.

- [Güvenlik Politikası](docs/security-policy.md)
- [Tehdit Modeli](docs/threat-model.md)
- [Mimari](docs/architecture.md)

Deep/Code profilleri production projelerinde varsayılan olarak engellenir; test modunda staging projesi otomatik seçilir.

---

## Lisans

Proprietary — Tüm hakları saklıdır.
