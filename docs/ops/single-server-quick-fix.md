# Tek Sunucu — Hızlı Onarım Notu

> **Amaç:** Restart veya SSH müdahalesi sonrası tüm domainlerin 502 vermesi.  
> Bu dosyayı okuyunca 2–5 dakikada düzelt.

## Sorun ne?

Sunucu (`87.106.10.169`) **tek Plesk/nginx/apache** katmanında 15+ domain barındırıyor:

```
İnternet → Nginx :443 → Apache :7080/7081 → App (Docker/PM2/Passenger)
```

**Kırılma tetikleyicileri:**
1. Restart sonrası **Apache kapalı** (`disabled`) kalır → nginx upstream bulamaz → **502**
2. Restart sonrası Plesk **SSL/nginx vhost boş** kalır → **443 dinlenmez** → tüm HTTPS ölür
3. SSH script’leri `systemctl restart nginx/apache` veya `httpdmng --reconfigure-all` → tüm domainler etkilenir

**Uygulamalar genelde ayaktadır:** SIBER Docker (:8010/:3011), Turbridge PM2 (:3006).

## Hızlı teşhis (SSH)

```bash
systemctl is-active apache2 nginx docker
ss -lntp | grep -E ':443|:7080'
curl -sf http://127.0.0.1:8010/api/v1/health
curl -sf http://127.0.0.1:3006/
curl -k -o /dev/null -w '%{http_code}\n' -H 'Host: siber.cloudnira.com' https://87.106.10.169/
```

| Belirti | Muhtemel neden |
|---------|----------------|
| apache2 `inactive` | Apache boot’ta kapalı |
| 443 yok | Plesk SSL config boş |
| :8010 OK ama site 502 | Apache/nginx proxy kırık |
| :3006 down | PM2 resurrect gerek |

## Hızlı onarım (sunucuda)

Guardrail script’leri kuruluysa:

```bash
/opt/siber/scripts/server/web-stack-recover.sh manual
# veya sadece healthcheck (otomatik recover tetikler)
/opt/siber/scripts/server/web-stack-healthcheck.sh
```

Manuel (guardrail yoksa):

```bash
systemctl enable apache2 nginx docker
systemctl start apache2
cd /opt/siber && docker compose -f docker-compose.prod.yml up -d
pm2 resurrect 2>/dev/null || true
plesk repair web -y
nginx -t && systemctl reload nginx
```

Tek domain değişikliği sonrası (güvenli):

```bash
/opt/siber/scripts/server/safe-vhost-reload.sh siber.cloudnira.com
# turbridge için:
/opt/siber/scripts/server/safe-vhost-reload.sh turbridge.de
```

## Yerel makineden kurulum / test

```powershell
$pw = (Get-Content "C:\GOGAPP\KleinRechnung\z-sifreler-vs.txt" | Select-Object -Index 1).Trim()
$env:DEPLOY_SSH_PASSWORD = $pw
node scripts/install-server-guardrails.cjs
node scripts/ssh-test-guardrails.cjs
node scripts/ssh-test-recover-simulation.cjs   # apache stop → auto recover test
```

Script’ler Windows’tan yüklenirse CRLF sorunu olabilir; installer otomatik `sed -i 's/\r$//'` uygular. Repo’da `scripts/server/*.sh` için `.gitattributes` LF zorlar.

## Otomatik önlemler (kurulu olmalı)

| Mekanizma | Ne yapar |
|-----------|----------|
| `siber-web-recover.service` | Boot sonrası stack + 443 onarımı |
| Cron `/etc/cron.d/siber-web-guard` | Her 5 dk healthcheck → gerekirse auto recover |
| `apache2/nginx/docker` enabled | Restart sonrası servisler açılsın |
| Log | `/var/log/siber-web-guard.log` |

## SSH / deploy kuralları (kırılmayı önle)

| Yapma | Yap |
|-------|-----|
| `systemctl restart nginx apache` | `nginx -t && systemctl reload nginx` |
| `httpdmng --reconfigure-all` | `--reconfigure-domain TEK_DOMAIN` |
| `/etc/nginx/plesk.conf.d/vhosts/*.conf` düzenle | Sadece `/var/www/vhosts/system/DOMAIN/conf/vhost_*.conf` |
| Global Passenger modülü kapat | Domain custom conf |
| Deploy sonrası SMTP unutma | `node scripts/ssh-configure-ionos-smtp.cjs` |

SIBER deploy (`deploy-pilot-production.cjs`) zaten güvenli pattern kullanır:
- Sadece `siber.cloudnira.com` vhost dosyaları
- `reconfigure-domain siber.cloudnira.com`
- `reload` nginx

## Doğrulama

```bash
curl -k -o /dev/null -w '%{http_code}\n' https://siber.cloudnira.com/api/v1/health
curl -k -o /dev/null -w '%{http_code}\n' https://turbridge.de/
curl -k -o /dev/null -w '%{http_code}\n' https://cloudnira.com/
tail -20 /var/log/siber-web-guard.log
systemctl status siber-web-recover.service
```

Beklenen: **200** (403/401/404 uygulama seviyesi, 502 değil).

## Dosya konumları

| Yer | Path |
|-----|------|
| Repo script’ler | `scripts/server/*.sh` |
| Sunucu | `/opt/siber/scripts/server/` |
| Kurulum | `scripts/install-server-guardrails.cjs` |
| Systemd | `/etc/systemd/system/siber-web-recover.service` |
| Cron | `/etc/cron.d/siber-web-guard` |

## Son bilinen olay

- **2026-07-26:** CloudPanel restart → Apache disabled + Plesk 443 boş → tüm siteler 502.  
  **Çözüm:** `plesk repair web -y` + Apache enable/start + nginx reload.
