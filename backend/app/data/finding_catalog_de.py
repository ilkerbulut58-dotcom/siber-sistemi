"""Deutscher Finding-Katalog und Multi-Hosting-Remediationsleitfäden."""

from __future__ import annotations

from typing import TypedDict


class FindingCatalogEntryDe(TypedDict):
    title_de: str
    description_de: str
    risk_explanation_de: str
    remediation_summary_de: str
    remediation_steps_de: list[str]
    config_file_paths_de: list[str]
    config_snippet: str | None
    hosting: str


def _generic_remediation_steps() -> list[str]:
    return [
        "Wählen Sie die passende Methode für Ihr Hosting: Nginx/Apache direkt, Panel (cPanel/Plesk), "
        "Cloudflare/CDN oder Anwendungsebene (Next.js, PHP usw.).",
        "Fügen Sie das Konfigurationsbeispiel in die entsprechende Datei oder das Panel ein "
        "(Pfade sind in config_file_paths nach Plattform getrennt).",
        "Testen Sie zuerst in Staging; sichern Sie die Produktivumgebung vor dem Rollout.",
        "Laden Sie den Server neu und validieren Sie mit einem erneuten SIBER-Scan.",
    ]


def _hosting_config_paths(domain: str) -> list[str]:
    return [
        f"[Nginx] /etc/nginx/sites-available/{domain} (server {{ }}-Block)",
        f"[Nginx/Plesk] Plesk → Websites & Domains → {domain} → Apache & nginx Settings → Additional nginx directives",
        f"[Apache] .htaccess im Document Root oder /etc/apache2/sites-available/{domain}.conf",
        f"[cPanel/WHM] Domains → {domain} → Apache Configuration / .htaccess Editor",
        f"[Cloudflare] Dashboard → {domain} → Rules → Transform Rules → Modify response header",
        "[IIS] site web.config → system.webServer/httpProtocol/customHeaders",
    ]


def _ssl_remediation_steps() -> list[str]:
    return [
        "Gültiges TLS-Zertifikat beschaffen (Let's Encrypt, Hosting-Anbieter oder CA).",
        "Zertifikat auf Server oder CDN installieren (Panel, certbot oder Anbieter-UI).",
        "HTTP-Traffic dauerhaft auf HTTPS umleiten (301 Redirect).",
        "Mit erneutem SIBER-Scan verifizieren.",
    ]


FINDING_CATALOG_DE: dict[str, FindingCatalogEntryDe] = {
    "missing-header-strict-transport-security": {
        "title_de": "HTTPS-Pflicht (HSTS) fehlt",
        "description_de": "Die Seite läuft über HTTPS, der Browser erhält aber keine dauerhafte Sicherheitsanweisung.",
        "risk_explanation_de": (
            "Fällt ein Nutzer einmal auf HTTP oder ein Angreifer greift das Netz an, "
            "bleibt die Verbindung angreifbarer. Gute Sicherheitspraxis, auch ohne Bankniveau."
        ),
        "remediation_summary_de": "HSTS-Header (Strict-Transport-Security) in der Antwort setzen.",
        "remediation_steps_de": _generic_remediation_steps(),
        "config_file_paths_de": [],
        "config_snippet": (
            'add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;'
        ),
        "hosting": "multi",
    },
    "missing-header-x-content-type-options": {
        "title_de": "Sicherheitsheader X-Content-Type-Options fehlt",
        "description_de": "Dem Browser fehlt die nosniff-Anweisung gegen MIME-Typ-Raten.",
        "risk_explanation_de": "Bei älteren Browsern steigt das MIME-Sniffing-Risiko leicht.",
        "remediation_summary_de": "Header X-Content-Type-Options: nosniff setzen.",
        "remediation_steps_de": _generic_remediation_steps(),
        "config_file_paths_de": [],
        "config_snippet": "add_header X-Content-Type-Options nosniff always;",
        "hosting": "multi",
    },
    "missing-header-x-frame-options": {
        "title_de": "Clickjacking-Schutz (X-Frame-Options) fehlt",
        "description_de": "Die Seite kann in fremden iframes eingebettet werden.",
        "risk_explanation_de": (
            "Bösartige Seiten können Ihre Seite unsichtbar einbetten und Nutzer "
            "zu falschen Klicks verleiten (Clickjacking)."
        ),
        "remediation_summary_de": "X-Frame-Options oder CSP frame-ancestors setzen.",
        "remediation_steps_de": _generic_remediation_steps(),
        "config_file_paths_de": [],
        "config_snippet": "add_header X-Frame-Options SAMEORIGIN always;",
        "hosting": "multi",
    },
    "missing-header-content-security-policy": {
        "title_de": "Content-Security-Policy (CSP) fehlt",
        "description_de": "Es gibt keine strikten Regeln, welche Skripte und Ressourcen geladen werden dürfen.",
        "risk_explanation_de": (
            "Bei XSS bleibt die Abwehr schwach. CSP muss korrekt sein; "
            "falsche CSP kann die Seite brechen — zuerst in Staging testen."
        ),
        "remediation_summary_de": "Mit einfacher CSP starten und schrittweise verschärfen.",
        "remediation_steps_de": [
            *_generic_remediation_steps()[:2],
            "Bei WordPress/Next.js können Inline-Script-Ausnahmen nötig sein.",
            *_generic_remediation_steps()[2:],
        ],
        "config_file_paths_de": [],
        "config_snippet": (
            'add_header Content-Security-Policy "default-src \'self\'; frame-ancestors \'self\';" always;'
        ),
        "hosting": "multi",
    },
    "missing-header-referrer-policy": {
        "title_de": "Referrer-Policy-Header fehlt",
        "description_de": "Es ist nicht festgelegt, wie viel URL beim Wechsel zu anderen Sites weitergegeben wird.",
        "risk_explanation_de": "Enthält die URL sensible Parameter (Token, E-Mail), können diese nach außen gelangen.",
        "remediation_summary_de": "Referrer-Policy-Header setzen.",
        "remediation_steps_de": _generic_remediation_steps(),
        "config_file_paths_de": [],
        "config_snippet": "add_header Referrer-Policy strict-origin-when-cross-origin always;",
        "hosting": "multi",
    },
    "server-disclosure": {
        "title_de": "Server-Software wird offengelegt",
        "description_de": "Die HTTP-Antwort zeigt Server-Typ/Version (z. B. nginx).",
        "risk_explanation_de": "Gibt Angreifern Hinweise; allein kein kritisches Risiko, aber besser verbergen.",
        "remediation_summary_de": "Server-Header generalisieren oder ausblenden.",
        "remediation_steps_de": [
            "Nginx: server_tokens off; (im http- oder server-Block)",
            "Apache: ServerTokens Prod, ServerSignature Off",
            "Bei CDN/Proxy Header-Ausblendung im Panel prüfen.",
            *_generic_remediation_steps()[2:],
        ],
        "config_file_paths_de": [],
        "config_snippet": "server_tokens off;",
        "hosting": "multi",
    },
    "insecure-cookie-flags": {
        "title_de": "Cookie-Sicherheitsflags fehlen",
        "description_de": "Set-Cookie enthält nicht alle empfohlenen Flags Secure, HttpOnly oder SameSite.",
        "risk_explanation_de": "Session-Cookies sind anfälliger für Diebstahl und CSRF.",
        "remediation_summary_de": "Cookie-Flags im Anwendungscode setzen.",
        "remediation_steps_de": [
            "Session-/Cookie-Einstellungen im Backend prüfen.",
            "Secure: nur HTTPS; HttpOnly: kein JS-Zugriff; SameSite: CSRF-Schutz.",
            "PHP: session_set_cookie_params; Node: cookie({ secure, httpOnly, sameSite }).",
            "Panel/CDN ändern das nicht — Fix liegt in der Anwendung.",
        ],
        "config_file_paths_de": [
            "[Anwendung] Session-/Cookie-Konfiguration (Middleware, session config)",
            "[PHP] php.ini oder session_set_cookie_params",
            "[Node.js] express-session / cookie-parser Einstellungen",
        ],
        "config_snippet": None,
        "hosting": "multi",
    },
    "no-http-redirect": {
        "title_de": "HTTP wird nicht auf HTTPS umgeleitet",
        "description_de": "http:// wird nicht automatisch auf https:// weitergeleitet.",
        "risk_explanation_de": "Nutzer und Suchmaschinen können unsicheres HTTP nutzen.",
        "remediation_summary_de": "HTTP-Anfragen dauerhaft auf HTTPS umleiten (301).",
        "remediation_steps_de": [
            "Nginx: return 301 https://$host$request_uri;",
            "Apache: RewriteEngine On + RewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [R=301,L]",
            "Plesk: Hosting Settings → Permanent SEO-safe 301 redirect to HTTPS",
            "cPanel: Domains → Redirects → HTTPS-Weiterleitung",
            "Cloudflare: SSL/TLS → Always Use HTTPS",
            *_generic_remediation_steps()[2:],
        ],
        "config_file_paths_de": [],
        "config_snippet": "return 301 https://$host$request_uri;",
        "hosting": "multi",
    },
    "weak-http-redirect": {
        "title_de": "HTTP-Weiterleitung führt nicht zu HTTPS",
        "description_de": "HTTP wird umgeleitet, das Ziel ist aber kein HTTPS.",
        "risk_explanation_de": "Die Redirect-Kette bleibt unsicher.",
        "remediation_summary_de": "301-Weiterleitung direkt auf https:// setzen.",
        "remediation_steps_de": [
            "Ziel-URL muss mit https:// beginnen.",
            "HTTPS-Weiterleitung im Hosting-Panel prüfen (Plesk, cPanel, Cloudflare).",
            "return/RewriteRule-Ziel in Nginx/Apache aktualisieren.",
        ],
        "config_file_paths_de": [],
        "config_snippet": "return 301 https://$host$request_uri;",
        "hosting": "multi",
    },
    "no-https": {
        "title_de": "Site nutzt kein HTTPS",
        "description_de": "Das Ziel wird nur per HTTP ausgeliefert.",
        "risk_explanation_de": "Der gesamte Traffic ist unverschlüsselt — hohes Risiko.",
        "remediation_summary_de": "TLS-Zertifikat installieren und HTTPS erzwingen.",
        "remediation_steps_de": _ssl_remediation_steps(),
        "config_file_paths_de": [],
        "config_snippet": None,
        "hosting": "multi",
    },
    "cert-expiring-soon": {
        "title_de": "SSL-Zertifikat läuft bald ab",
        "description_de": "Die TLS-Gültigkeit endet in weniger als 30 Tagen.",
        "risk_explanation_de": "Nach Ablauf zeigen Browser „Nicht sicher“-Warnungen.",
        "remediation_summary_de": "Zertifikat erneuern (Let's Encrypt, Hosting-Anbieter oder CA).",
        "remediation_steps_de": [
            "Erneuerung im Hosting-Panel starten (Plesk, cPanel, Cloudflare).",
            "Alternativ: certbot renew (Let's Encrypt auf dem Server).",
            "Automatische Erneuerung (cron/systemd timer) sicherstellen.",
        ],
        "config_file_paths_de": [],
        "config_snippet": None,
        "hosting": "multi",
    },
    "cert-invalid": {
        "title_de": "SSL-Zertifikat ungültig",
        "description_de": "Das TLS-Zertifikat konnte nicht verifiziert werden.",
        "risk_explanation_de": "Besucher können der Verbindung nicht vertrauen.",
        "remediation_summary_de": "Gültiges Zertifikat installieren.",
        "remediation_steps_de": _ssl_remediation_steps(),
        "config_file_paths_de": [],
        "config_snippet": None,
        "hosting": "multi",
    },
    "http-5xx": {
        "title_de": "Server-Fehlerantwort (5xx)",
        "description_de": "Die Site antwortete mit einem Serverfehler.",
        "risk_explanation_de": "Die Site kann teilweise oder vollständig nicht erreichbar sein.",
        "remediation_summary_de": "Server- und Anwendungslogs prüfen.",
        "remediation_steps_de": [
            "Webserver error.log: /var/log/nginx/error.log oder Apache error.log",
            "Hosting-Panel-Logs (Plesk, cPanel → Errors)",
            "Anwendungs-/Container-Logs prüfen.",
            "Letztes Deployment oder Config-Änderung nachverfolgen.",
        ],
        "config_file_paths_de": [],
        "config_snippet": None,
        "hosting": "multi",
    },
    "http-unreachable": {
        "title_de": "Site nicht erreichbar",
        "description_de": "Die Ziel-URL antwortete während des Scans nicht.",
        "risk_explanation_de": "Site offline, DNS-Fehler oder Firewall-Blockade möglich.",
        "remediation_summary_de": "DNS, Serverstatus und Firewall-Regeln prüfen.",
        "remediation_steps_de": [
            "Site manuell im Browser öffnen.",
            "DNS-Einträge (A/AAAA/CNAME) validieren.",
            "Domain- und Serverstatus im Hosting-Panel prüfen.",
            "Firewall/Sicherheitsgruppen für Ports 80/443 prüfen.",
        ],
        "config_file_paths_de": [],
        "config_snippet": None,
        "hosting": "multi",
    },
    "x-powered-by-disclosure": {
        "title_de": "X-Powered-By-Header gibt Technologie preis",
        "description_de": "Die Antwort zeigt die verwendete Technologie (PHP, ASP.NET usw.).",
        "risk_explanation_de": "Erleichtert Angreifern die Zielauswahl.",
        "remediation_summary_de": "X-Powered-By-Header entfernen oder ausblenden.",
        "remediation_steps_de": [
            "PHP: expose_php = Off (php.ini)",
            "Nginx: proxy_hide_header X-Powered-By; (hinter Reverse Proxy)",
            "Apache: Header unset X-Powered-By",
            "ASP.NET/IIS: web.config removeServerHeader oder customHeaders",
        ],
        "config_file_paths_de": [],
        "config_snippet": "proxy_hide_header X-Powered-By;",
        "hosting": "multi",
    },
}

SEVERITY_LABEL_DE = {
    "critical": "Kritisch",
    "high": "Hoch",
    "medium": "Mittel",
    "low": "Niedrig",
    "info": "Info",
}


def get_catalog_entry(rule_id: str, domain: str) -> FindingCatalogEntryDe | None:
    entry = FINDING_CATALOG_DE.get(rule_id)
    if entry is None:
        return None
    resolved = dict(entry)
    if not resolved["config_file_paths_de"]:
        resolved["config_file_paths_de"] = _hosting_config_paths(domain)
    else:
        resolved["config_file_paths_de"] = [
            p.replace("{domain}", domain) for p in resolved["config_file_paths_de"]
        ]
    return resolved  # type: ignore[return-value]
