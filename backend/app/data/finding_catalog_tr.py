"""Türkçe bulgu kataloğu ve çoklu hosting ortamı çözüm rehberleri."""

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


def _generic_remediation_steps() -> list[str]:
    return [
        "Hosting ortamınıza uygun yöntemi seçin: doğrudan Nginx/Apache, cPanel/Plesk gibi panel, "
        "Cloudflare/CDN veya uygulama katmanı (Next.js, PHP vb.).",
        "Aşağıdaki yapılandırma örneğini ilgili dosyaya veya panele ekleyin "
        "(konumlar config_file_paths listesinde platforma göre ayrılmıştır).",
        "Önce test veya staging ortamında deneyin; canlıya almadan önce yedek alın.",
        "Sunucuyu yeniden yükleyin ve SIBER'de yeniden tarayarak doğrulayın.",
    ]


def _hosting_config_paths(domain: str) -> list[str]:
    return [
        f"[Nginx] /etc/nginx/sites-available/{domain} (server {{ }} bloğu)",
        f"[Nginx/Plesk] Plesk → Websites & Domains → {domain} → Apache & nginx Settings → Additional nginx directives",
        f"[Apache] Site kökünde .htaccess veya /etc/apache2/sites-available/{domain}.conf",
        f"[cPanel/WHM] Domains → {domain} → Apache Configuration / .htaccess Editor",
        f"[Cloudflare] Dashboard → {domain} → Rules → Transform Rules → Modify response header",
        f"[IIS] site web.config → system.webServer/httpProtocol/customHeaders",
    ]


def _ssl_remediation_steps() -> list[str]:
    return [
        "Geçerli bir TLS sertifikası edinin (Let's Encrypt, hosting sağlayıcı veya CA).",
        "Sertifikayı sunucunuza veya CDN'inize yükleyin (panel, certbot veya sağlayıcı arayüzü).",
        "HTTP trafiğini HTTPS'e yönlendirin (301 redirect).",
        "SIBER'de yeniden tarayarak doğrulayın.",
    ]


FINDING_CATALOG_TR: dict[str, FindingCatalogEntry] = {
    "missing-header-strict-transport-security": {
        "title_tr": "HTTPS zorunluluğu (HSTS) ayarı eksik",
        "description_tr": "Site HTTPS ile açılıyor ancak tarayıcıya kalıcı güvenli bağlantı talimatı verilmiyor.",
        "risk_explanation_tr": (
            "Kullanıcı bir kez HTTP bağlantısına düşerse veya ağ saldırısı olursa "
            "bağlantı zayıf kalabilir. Bankacılık seviyesi değil ama iyi bir güvenlik alışkanlığıdır."
        ),
        "remediation_summary_tr": "Yanıta HSTS (Strict-Transport-Security) header ekleyin.",
        "remediation_steps_tr": _generic_remediation_steps(),
        "config_file_paths_tr": [],
        "config_snippet": (
            'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
        ),
        "hosting": "multi",
    },
    "missing-header-x-content-type-options": {
        "title_tr": "X-Content-Type-Options güvenlik başlığı eksik",
        "description_tr": "Tarayıcıya dosya türünü tahmin etmemesi için nosniff talimatı verilmiyor.",
        "risk_explanation_tr": "Eski tarayıcılarda MIME karışıklığı riski hafifçe artar.",
        "remediation_summary_tr": "X-Content-Type-Options: nosniff header ekleyin.",
        "remediation_steps_tr": _generic_remediation_steps(),
        "config_file_paths_tr": [],
        "config_snippet": "add_header X-Content-Type-Options nosniff always;",
        "hosting": "multi",
    },
    "missing-header-x-frame-options": {
        "title_tr": "Clickjacking koruması (X-Frame-Options) eksik",
        "description_tr": "Sitenizin başka bir sitede gizli çerçeve (iframe) içinde açılması engellenmiyor.",
        "risk_explanation_tr": (
            "Kötü niyetli bir site sizin sayfanızı görünmez çerçevede gösterip "
            "kullanıcıyı yanlış tıklamaya yönlendirebilir (clickjacking)."
        ),
        "remediation_summary_tr": "X-Frame-Options veya CSP frame-ancestors ekleyin.",
        "remediation_steps_tr": _generic_remediation_steps(),
        "config_file_paths_tr": [],
        "config_snippet": "add_header X-Frame-Options SAMEORIGIN always;",
        "hosting": "multi",
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
            *_generic_remediation_steps()[:2],
            "WordPress/Next.js kullanıyorsanız inline script izinleri gerekebilir.",
            *_generic_remediation_steps()[2:],
        ],
        "config_file_paths_tr": [],
        "config_snippet": (
            'add_header Content-Security-Policy "default-src \'self\'; frame-ancestors \'self\';" always;'
        ),
        "hosting": "multi",
    },
    "missing-header-referrer-policy": {
        "title_tr": "Referrer-Policy başlığı eksik",
        "description_tr": "Başka siteye giderken URL'nizin ne kadar paylaşılacağı belirtilmemiş.",
        "risk_explanation_tr": "URL'de hassas parametre varsa (token, e-posta) dış sitelere sızabilir.",
        "remediation_summary_tr": "Referrer-Policy header ekleyin.",
        "remediation_steps_tr": _generic_remediation_steps(),
        "config_file_paths_tr": [],
        "config_snippet": "add_header Referrer-Policy strict-origin-when-cross-origin always;",
        "hosting": "multi",
    },
    "server-disclosure": {
        "title_tr": "Sunucu yazılım bilgisi görünüyor",
        "description_tr": "HTTP yanıtında sunucu tipi/sürümü (ör. nginx) açıkça belirtiliyor.",
        "risk_explanation_tr": "Saldırganlara ipucu verir; tek başına açık sayılmaz ama gizlemek iyidir.",
        "remediation_summary_tr": "Server header'ını genelleştirin veya gizleyin.",
        "remediation_steps_tr": [
            "Nginx: server_tokens off; (http veya server bloğunda)",
            "Apache: ServerTokens Prod, ServerSignature Off",
            "CDN/proxy kullanıyorsanız ilgili panelden header gizleme seçeneğini kontrol edin.",
            *_generic_remediation_steps()[2:],
        ],
        "config_file_paths_tr": [],
        "config_snippet": "server_tokens off;",
        "hosting": "multi",
    },
    "insecure-cookie-flags": {
        "title_tr": "Çerez güvenlik bayrakları eksik",
        "description_tr": "Set-Cookie yanıtında Secure, HttpOnly veya SameSite bayrakları eksik.",
        "risk_explanation_tr": "Oturum çerezleri çalınmaya veya CSRF saldırılarına daha açık olabilir.",
        "remediation_summary_tr": "Uygulama kodunda çerez bayraklarını ayarlayın.",
        "remediation_steps_tr": [
            "Kaynak kodda oturum/cookie ayarlarını kontrol edin (backend framework).",
            "Secure: yalnızca HTTPS; HttpOnly: JavaScript erişemez; SameSite: CSRF koruması.",
            "PHP: session_set_cookie_params; Node: cookie({ secure, httpOnly, sameSite }).",
            "Panel/CDN bu ayarı değiştirmez — düzeltme uygulama katmanındadır.",
        ],
        "config_file_paths_tr": [
            "[Uygulama] Backend oturum/cookie yapılandırması (middleware, session config)",
            "[PHP] php.ini veya session_set_cookie_params",
            "[Node.js] express-session / cookie-parser ayarları",
        ],
        "config_snippet": None,
        "hosting": "multi",
    },
    "no-http-redirect": {
        "title_tr": "HTTP trafiği HTTPS'e yönlendirilmiyor",
        "description_tr": "http:// sürümü otomatik olarak https:// adresine yönlendirilmiyor.",
        "risk_explanation_tr": "Kullanıcılar ve arama motorları güvensiz HTTP ile siteye girebilir.",
        "remediation_summary_tr": "HTTP isteklerini kalıcı olarak HTTPS'e yönlendirin (301).",
        "remediation_steps_tr": [
            "Nginx: return 301 https://$host$request_uri;",
            "Apache: RewriteEngine On + RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]",
            "Plesk: Hosting Settings → Permanent SEO-safe 301 redirect to HTTPS",
            "cPanel: Domains → Redirects → HTTPS yönlendirmesi",
            "Cloudflare: SSL/TLS → Always Use HTTPS",
            *_generic_remediation_steps()[2:],
        ],
        "config_file_paths_tr": [],
        "config_snippet": "return 301 https://$host$request_uri;",
        "hosting": "multi",
    },
    "weak-http-redirect": {
        "title_tr": "HTTP yönlendirmesi HTTPS'e gitmiyor",
        "description_tr": "HTTP isteği yönlendiriliyor ama hedef HTTPS değil.",
        "risk_explanation_tr": "Yönlendirme zinciri güvensiz kalır.",
        "remediation_summary_tr": "301 yönlendirmesini doğrudan https:// adresine ayarlayın.",
        "remediation_steps_tr": [
            "Yönlendirme hedefinin https:// ile başladığından emin olun.",
            "Hosting panelinizde (Plesk, cPanel, Cloudflare vb.) HTTPS yönlendirmesini kontrol edin.",
            "Nginx/Apache yapılandırmasında return/RewriteRule hedefini güncelleyin.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": "return 301 https://$host$request_uri;",
        "hosting": "multi",
    },
    "no-https": {
        "title_tr": "Site HTTPS kullanmıyor",
        "description_tr": "Hedef adres düz HTTP ile sunuluyor.",
        "risk_explanation_tr": "Tüm trafik şifrelenmeden gider; ciddi risk.",
        "remediation_summary_tr": "TLS sertifikası kurun ve HTTPS zorunlu kılın.",
        "remediation_steps_tr": _ssl_remediation_steps(),
        "config_file_paths_tr": [],
        "config_snippet": None,
        "hosting": "multi",
    },
    "cert-expiring-soon": {
        "title_tr": "SSL sertifikası yakında sona eriyor",
        "description_tr": "TLS sertifikasının geçerlilik süresi 30 günden az.",
        "risk_explanation_tr": "Süre dolunca tarayıcılar 'Güvenli değil' uyarısı gösterir.",
        "remediation_summary_tr": "Sertifikayı yenileyin (Let's Encrypt, hosting sağlayıcı veya CA).",
        "remediation_steps_tr": [
            "Hosting panelinizden (Plesk, cPanel, Cloudflare) sertifika yenilemesini başlatın.",
            "Alternatif: certbot renew (sunucuda Let's Encrypt kullanıyorsanız).",
            "Otomatik yenileme cron/systemd timer kurulu olduğundan emin olun.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": None,
        "hosting": "multi",
    },
    "cert-invalid": {
        "title_tr": "SSL sertifikası geçersiz",
        "description_tr": "TLS sertifikası doğrulanamadı.",
        "risk_explanation_tr": "Ziyaretçiler siteye güvenle bağlanamaz.",
        "remediation_summary_tr": "Geçerli bir sertifika yükleyin.",
        "remediation_steps_tr": _ssl_remediation_steps(),
        "config_file_paths_tr": [],
        "config_snippet": None,
        "hosting": "multi",
    },
    "http-5xx": {
        "title_tr": "Sunucu hata yanıtı (5xx)",
        "description_tr": "Site isteğe sunucu hatası ile yanıt verdi.",
        "risk_explanation_tr": "Site kısmen veya tamamen erişilemez olabilir.",
        "remediation_summary_tr": "Sunucu ve uygulama loglarını kontrol edin.",
        "remediation_steps_tr": [
            "Web sunucusu error log: /var/log/nginx/error.log veya Apache error.log",
            "Hosting paneli logları (Plesk, cPanel → Errors)",
            "Uygulama/container loglarına bakın.",
            "Son dağıtım veya yapılandırma değişikliğini gözden geçirin.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": None,
        "hosting": "multi",
    },
    "http-unreachable": {
        "title_tr": "Siteye erişilemedi",
        "description_tr": "Tarama sırasında hedef URL yanıt vermedi.",
        "risk_explanation_tr": "Site kapalı, DNS hatalı veya firewall engelliyor olabilir.",
        "remediation_summary_tr": "DNS, sunucu durumu ve firewall kurallarını kontrol edin.",
        "remediation_steps_tr": [
            "Tarayıcıdan siteyi manuel açmayı deneyin.",
            "DNS kayıtlarını (A/AAAA/CNAME) doğrulayın.",
            "Hosting sağlayıcı panelinde domain ve sunucu durumunu kontrol edin.",
            "Firewall / güvenlik grubu kurallarında 80/443 portlarını kontrol edin.",
        ],
        "config_file_paths_tr": [],
        "config_snippet": None,
        "hosting": "multi",
    },
    "x-powered-by-disclosure": {
        "title_tr": "X-Powered-By başlığı bilgi sızdırıyor",
        "description_tr": "Yanıtta kullanılan teknoloji (PHP, ASP.NET vb.) görünüyor.",
        "risk_explanation_tr": "Saldırganlara hedef seçiminde ipucu verir.",
        "remediation_summary_tr": "X-Powered-By header'ını kaldırın veya gizleyin.",
        "remediation_steps_tr": [
            "PHP: expose_php = Off (php.ini)",
            "Nginx: proxy_hide_header X-Powered-By; (reverse proxy arkasında)",
            "Apache: Header unset X-Powered-By",
            "ASP.NET/IIS: web.config removeServerHeader veya customHeaders",
        ],
        "config_file_paths_tr": [],
        "config_snippet": "proxy_hide_header X-Powered-By;",
        "hosting": "multi",
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
        resolved["config_file_paths_tr"] = _hosting_config_paths(domain)
    else:
        resolved["config_file_paths_tr"] = [
            p.replace("{domain}", domain) for p in resolved["config_file_paths_tr"]
        ]
    return resolved  # type: ignore[return-value]
