"""Türkçe bulgu kataloğu ve Plesk çözüm rehberleri."""

from __future__ import annotations

from typing import TypedDict


class FindingCatalogEntry(TypedDict):
    title_tr: str
    description_tr: str
    risk_explanation_tr: str
    remediation_summary_tr: str
    remediation_steps_tr: list[str]
    config_file_paths_tr: list[str]
    config_snippet: str | None
    hosting: str


def _plesk_paths(domain: str) -> list[str]:
    return [
        f"Plesk → Websites & Domains → {domain} → Apache & nginx Settings",
        f"/var/www/vhosts/system/{domain}/conf/vhost_nginx.conf",
        f"/var/www/vhosts/cloudnira.com/{domain}/ (document root — statik dosyalar için)",
    ]


def _nginx_extra_directives_hint() -> str:
    return (
        'Plesk panelinde "Additional nginx directives" (Ek nginx yönergeleri) '
        "bölümüne aşağıdaki satırları ekleyin."
    )


FINDING_CATALOG_TR: dict[str, FindingCatalogEntry] = {
    "missing-header-strict-transport-security": {
        "title_tr": "HTTPS zorunluluğu (HSTS) ayarı eksik",
        "description_tr": "Site HTTPS ile açılıyor ancak tarayıcıya kalıcı güvenli bağlantı talimatı verilmiyor.",
        "risk_explanation_tr": (
            "Kullanıcı bir kez HTTP bağlantısına düşerse veya ağ saldırısı olursa "
            "bağlantı zayıf kalabilir. Bankacılık seviyesi değil ama iyi bir güvenlik alışkanlığıdır."
        ),
        "remediation_summary_tr": "Nginx/Apache yanıtına HSTS header ekleyin.",
        "remediation_steps_tr": [
            "Plesk'e giriş yapın.",
            "Domains → sitenizi seçin → Apache & nginx Settings.",
            _nginx_extra_directives_hint(),
            "Değişikliği kaydedin ve nginx'i yeniden yükleyin (Plesk genelde otomatik yapar).",
            "SIBER'de bu bulgu için 'Yeniden tara' ile doğrulayın.",
        ],
        "config_file_paths_tr": [],  # filled by template
        "config_snippet": (
            'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
        ),
        "hosting": "plesk",
    },
    "missing-header-x-content-type-options": {
        "title_tr": "X-Content-Type-Options güvenlik başlığı eksik",
        "description_tr": "Tarayıcıya dosya türünü tahmin etmemesi için nosniff talimatı verilmiyor.",
        "risk_explanation_tr": "Eski tarayıcılarda MIME karışıklığı riski hafifçe artar.",
        "remediation_summary_tr": "add_header X-Content-Type-Options nosniff ekleyin.",
        "remediation_steps_tr": [
            "Plesk → siteniz → Apache & nginx Settings.",
            _nginx_extra_directives_hint(),
            "Kaydedin ve yeniden tarayın.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": "add_header X-Content-Type-Options nosniff always;",
        "hosting": "plesk",
    },
    "missing-header-x-frame-options": {
        "title_tr": "Clickjacking koruması (X-Frame-Options) eksik",
        "description_tr": "Sitenizin başka bir sitede gizli çerçeve (iframe) içinde açılması engellenmiyor.",
        "risk_explanation_tr": (
            "Kötü niyetli bir site sizin sayfanızı görünmez çerçevede gösterip "
            "kullanıcıyı yanlış tıklamaya yönlendirebilir (clickjacking)."
        ),
        "remediation_summary_tr": "X-Frame-Options veya CSP frame-ancestors ekleyin.",
        "remediation_steps_tr": [
            "Plesk → siteniz → Apache & nginx Settings.",
            _nginx_extra_directives_hint(),
            "Form veya giriş sayfası varsa bu ayar özellikle önemlidir.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": "add_header X-Frame-Options SAMEORIGIN always;",
        "hosting": "plesk",
    },
    "missing-header-content-security-policy": {
        "title_tr": "İçerik güvenlik politikası (CSP) eksik",
        "description_tr": "Hangi script ve kaynakların yüklenebileceğine dair sıkı kural tanımlı değil.",
        "risk_explanation_tr": (
            "XSS (zararlı script enjeksiyonu) olursa savunma zayıf kalır. "
            "CSP doğru ayarlanmalıdır; yanlış CSP siteyi bozabilir — önce test ortamında deneyin."
        ),
        "remediation_summary_tr": "Basit bir CSP ile başlayın, sonra sıkılaştırın.",
        "remediation_steps_tr": [
            "Önce staging/test ortamında deneyin.",
            "Plesk → Apache & nginx Settings → Additional nginx directives.",
            "Aşağıdaki basit CSP ile başlayın; site kırılırsa script kaynaklarını genişletin.",
            "WordPress/Next.js kullanıyorsanız inline script izinleri gerekebilir.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": (
            'add_header Content-Security-Policy "default-src \'self\'; frame-ancestors \'self\';" always;'
        ),
        "hosting": "plesk",
    },
    "missing-header-referrer-policy": {
        "title_tr": "Referrer-Policy başlığı eksik",
        "description_tr": "Başka siteye giderken URL'nizin ne kadar paylaşılacağı belirtilmemiş.",
        "risk_explanation_tr": "URL'de hassas parametre varsa (token, e-posta) dış sitelere sızabilir.",
        "remediation_summary_tr": "Referrer-Policy header ekleyin.",
        "remediation_steps_tr": [
            "Plesk → Apache & nginx Settings.",
            _nginx_extra_directives_hint(),
        ],
        "config_file_paths_tr": [],
        "config_snippet": "add_header Referrer-Policy strict-origin-when-cross-origin always;",
        "hosting": "plesk",
    },
    "server-disclosure": {
        "title_tr": "Sunucu yazılım bilgisi görünüyor",
        "description_tr": "HTTP yanıtında sunucu tipi/sürümü (ör. nginx) açıkça belirtiliyor.",
        "risk_explanation_tr": "Saldırganlara ipucu verir; tek başına açık sayılmaz ama gizlemek iyidir.",
        "remediation_summary_tr": "Server header'ını genelleştirin veya gizleyin.",
        "remediation_steps_tr": [
            "Plesk → Apache & nginx Settings → nginx.conf veya ek direktifler.",
            "server_tokens off; ayarını kontrol edin.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": "server_tokens off;",
        "hosting": "plesk",
    },
    "insecure-cookie-flags": {
        "title_tr": "Çerez güvenlik bayrakları eksik",
        "description_tr": "Set-Cookie yanıtında Secure, HttpOnly veya SameSite bayrakları eksik.",
        "risk_explanation_tr": "Oturum çerezleri çalınmaya veya CSRF saldırılarına daha açık olabilir.",
        "remediation_summary_tr": "Uygulama kodunda veya sunucu yapılandırmasında çerez bayraklarını ayarlayın.",
        "remediation_steps_tr": [
            "Kaynak kodda oturum/cookie ayarlarını kontrol edin (backend framework).",
            "Secure: yalnızca HTTPS; HttpOnly: JavaScript erişemez; SameSite: CSRF koruması.",
            "PHP: session_set_cookie_params; Node: cookie({ secure, httpOnly, sameSite }).",
        ],
        "config_file_paths_tr": [
            "Kaynak kod: backend oturum/cookie yapılandırması",
            "Örnek: app/config/session.* veya middleware",
        ],
        "config_snippet": None,
        "hosting": "plesk",
    },
    "no-http-redirect": {
        "title_tr": "HTTP trafiği HTTPS'e yönlendirilmiyor",
        "description_tr": "http:// sürümü otomatik olarak https:// adresine yönlendirilmiyor.",
        "risk_explanation_tr": "Kullanıcılar ve arama motorları güvensiz HTTP ile siteye girebilir.",
        "remediation_summary_tr": "Plesk'te 'Permanent SEO-safe 301 redirect from HTTP to HTTPS' açın.",
        "remediation_steps_tr": [
            "Plesk → siteniz → Hosting Settings.",
            "'Permanent SEO-safe 301 redirect from HTTP to HTTPS' seçeneğini etkinleştirin.",
            "Alternatif: nginx'te return 301 https://$host$request_uri;",
        ],
        "config_file_paths_tr": [],
        "config_snippet": "return 301 https://$host$request_uri;",
        "hosting": "plesk",
    },
    "weak-http-redirect": {
        "title_tr": "HTTP yönlendirmesi HTTPS'e gitmiyor",
        "description_tr": "HTTP isteği yönlendiriliyor ama hedef HTTPS değil.",
        "risk_explanation_tr": "Yönlendirme zinciri güvensiz kalır.",
        "remediation_summary_tr": "301 yönlendirmesini doğrudan https:// adresine ayarlayın.",
        "remediation_steps_tr": [
            "Plesk Hosting Settings → HTTPS yönlendirmesini kontrol edin.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": "return 301 https://$host$request_uri;",
        "hosting": "plesk",
    },
    "no-https": {
        "title_tr": "Site HTTPS kullanmıyor",
        "description_tr": "Hedef adres düz HTTP ile sunuluyor.",
        "risk_explanation_tr": "Tüm trafik şifrelenmeden gider; ciddi risk.",
        "remediation_summary_tr": "Plesk'te SSL/TLS sertifikası kurun ve HTTPS zorunlu kılın.",
        "remediation_steps_tr": [
            "Plesk → SSL/TLS Certificates → Let's Encrypt ile sertifika alın.",
            "Hosting Settings → HTTPS yönlendirmesini açın.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": None,
        "hosting": "plesk",
    },
    "cert-expiring-soon": {
        "title_tr": "SSL sertifikası yakında sona eriyor",
        "description_tr": "TLS sertifikasının geçerlilik süresi 30 günden az.",
        "risk_explanation_tr": "Süre dolunca tarayıcılar 'Güvenli değil' uyarısı gösterir.",
        "remediation_summary_tr": "Plesk'ten sertifikayı yenileyin (Let's Encrypt otomatik olabilir).",
        "remediation_steps_tr": [
            "Plesk → SSL/TLS → sertifikayı yenileyin veya otomatik yenilemeyi açın.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": None,
        "hosting": "plesk",
    },
    "cert-invalid": {
        "title_tr": "SSL sertifikası geçersiz",
        "description_tr": "TLS sertifikası doğrulanamadı.",
        "risk_explanation_tr": "Ziyaretçiler siteye güvenle bağlanamaz.",
        "remediation_summary_tr": "Geçerli bir sertifika yükleyin.",
        "remediation_steps_tr": [
            "Plesk → SSL/TLS → yeni sertifika yükleyin veya Let's Encrypt kullanın.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": None,
        "hosting": "plesk",
    },
    "http-5xx": {
        "title_tr": "Sunucu hata yanıtı (5xx)",
        "description_tr": "Site isteğe sunucu hatası ile yanıt verdi.",
        "risk_explanation_tr": "Site kısmen veya tamamen erişilemez olabilir.",
        "remediation_summary_tr": "Sunucu ve uygulama loglarını kontrol edin.",
        "remediation_steps_tr": [
            "Plesk → Logs → error_log dosyasını inceleyin.",
            "Uygulama/container loglarına bakın.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": None,
        "hosting": "plesk",
    },
    "http-unreachable": {
        "title_tr": "Siteye erişilemedi",
        "description_tr": "Tarama sırasında hedef URL yanıt vermedi.",
        "risk_explanation_tr": "Site kapalı, DNS hatalı veya firewall engelliyor olabilir.",
        "remediation_summary_tr": "DNS, sunucu durumu ve firewall kurallarını kontrol edin.",
        "remediation_steps_tr": [
            "Tarayıcıdan siteyi manuel açmayı deneyin.",
            "Plesk'te domain durumunu kontrol edin.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": None,
        "hosting": "plesk",
    },
    "x-powered-by-disclosure": {
        "title_tr": "X-Powered-By başlığı bilgi sızdırıyor",
        "description_tr": "Yanıtta kullanılan teknoloji (PHP, ASP.NET vb.) görünüyor.",
        "risk_explanation_tr": "Saldırganlara hedef seçiminde ipucu verir.",
        "remediation_summary_tr": "X-Powered-By header'ını kaldırın veya gizleyin.",
        "remediation_steps_tr": [
            "PHP: expose_php = Off (php.ini)",
            "Nginx/Apache: proxy_hide_header veya Header unset",
        ],
        "config_file_paths_tr": [],
        "config_snippet": "proxy_hide_header X-Powered-By;",
        "hosting": "plesk",
    },
}

SEVERITY_LABEL_TR = {
    "critical": "Kritik",
    "high": "Yüksek",
    "medium": "Orta",
    "low": "Düşük",
    "info": "Bilgi",
}


def get_catalog_entry(rule_id: str, domain: str) -> FindingCatalogEntry | None:
    entry = FINDING_CATALOG_TR.get(rule_id)
    if entry is None:
        return None
    resolved = dict(entry)
    if not resolved["config_file_paths_tr"]:
        resolved["config_file_paths_tr"] = _plesk_paths(domain)
    else:
        resolved["config_file_paths_tr"] = [
            p.replace("{domain}", domain) for p in resolved["config_file_paths_tr"]
        ]
    return resolved  # type: ignore[return-value]
