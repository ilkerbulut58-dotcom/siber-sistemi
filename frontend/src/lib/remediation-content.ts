import type { Locale } from "@/lib/i18n/types";

export interface RemediationContent {
  nginxSteps: string[];
  apacheSteps: string[];
  cpanelSteps: string[];
  cloudflareSteps: string[];
  iisSteps: string[];
  pleskSteps: string[];
  androidSteps: string[];
  iosSteps: string[];
}

export const REMEDIATION_CONTENT: Record<Locale, RemediationContent> = {
  tr: {
    nginxSteps: [
      "Nginx site yapılandırmasında server { } veya ilgili location bloğuna ekleyin.",
      "Dosya örneği: /etc/nginx/sites-available/siteniz (sites-enabled'a symlink)",
      "Test: nginx -t — ardından: systemctl reload nginx",
    ],
    apacheSteps: [
      "Site kökündeki .htaccess veya Apache VirtualHost yapılandırmasına ekleyin.",
      "mod_headers etkin olmalı: a2enmod headers && systemctl reload apache2",
    ],
    cpanelSteps: [
      "cPanel → Domains → ilgili domain → Apache Configuration veya .htaccess Editor",
      "WHM kullanıyorsanız: Apache Configuration veya Include Editor",
    ],
    cloudflareSteps: [
      "Cloudflare Dashboard → siteniz → Rules → Transform Rules",
      "Modify response header ile gerekli güvenlik başlığını ekleyin.",
      "Alternatif: Configuration → SSL/TLS (HTTPS yönlendirme için)",
    ],
    iisSteps: [
      "site web.config dosyasında system.webServer/httpProtocol/customHeaders bölümünü düzenleyin.",
      "IIS Manager → HTTP Response Headers ile de eklenebilir.",
    ],
    pleskSteps: [
      "Plesk → Websites & Domains → domain → Apache & nginx Settings",
      "Additional nginx directives veya Additional Apache directives bölümüne ekleyin.",
    ],
    androidSteps: [
      "AndroidManifest.xml ve build.gradle dosyalarını inceleyin.",
      "Release build'de debuggable=false, allowBackup=false ayarlayın.",
      "Secrets'ları kod tabanından kaldırın ve sızdırılmış anahtarları rotate edin.",
    ],
    iosSteps: [
      "Info.plist ve Xcode build ayarlarını kontrol edin.",
      "App Transport Security (ATS) kurallarını sıkılaştırın.",
      "Release yapılandırmasında debug sembollerini ve gereksiz izinleri kaldırın.",
    ],
  },
  de: {
    nginxSteps: [
      "In der Nginx-Site-Konfiguration im server { }- oder location-Block ergänzen.",
      "Beispieldatei: /etc/nginx/sites-available/ihre-site (Symlink nach sites-enabled)",
      "Test: nginx -t — danach: systemctl reload nginx",
    ],
    apacheSteps: [
      "In .htaccess im Document Root oder Apache VirtualHost einfügen.",
      "mod_headers aktivieren: a2enmod headers && systemctl reload apache2",
    ],
    cpanelSteps: [
      "cPanel → Domains → Domain → Apache Configuration oder .htaccess Editor",
      "Bei WHM: Apache Configuration oder Include Editor",
    ],
    cloudflareSteps: [
      "Cloudflare Dashboard → Site → Rules → Transform Rules",
      "Erforderlichen Sicherheits-Header per Modify response header setzen.",
      "Alternative: Configuration → SSL/TLS (für HTTPS-Weiterleitung)",
    ],
    iisSteps: [
      "In web.config unter system.webServer/httpProtocol/customHeaders anpassen.",
      "Alternativ über IIS Manager → HTTP Response Headers.",
    ],
    pleskSteps: [
      "Plesk → Websites & Domains → Domain → Apache & nginx Settings",
      "Additional nginx directives oder Additional Apache directives",
    ],
    androidSteps: [
      "AndroidManifest.xml und build.gradle prüfen.",
      "Im Release debuggable=false, allowBackup=false setzen.",
      "Secrets aus dem Code entfernen und geleakte Keys rotieren.",
    ],
    iosSteps: [
      "Info.plist und Xcode-Build-Einstellungen prüfen.",
      "App Transport Security (ATS) verschärfen.",
      "Debug-Symbole und unnötige Berechtigungen im Release entfernen.",
    ],
  },
};
