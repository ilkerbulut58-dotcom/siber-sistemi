/**
 * Read-only live pre-check for expert test readiness (no secrets in output).
 */
const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');
const password = process.env.DEPLOY_SSH_PASSWORD;

function exec(conn, cmd) {
  return new Promise((resolve, reject) => {
    conn.exec(cmd, (err, stream) => {
      if (err) return reject(err);
      let out = '';
      stream.on('data', (d) => { out += d.toString(); process.stdout.write(d); });
      stream.stderr.on('data', (d) => { out += d.toString(); process.stderr.write(d); });
      stream.on('close', (code) => resolve({ code, out }));
    });
  });
}

const cmd = `
set -euo pipefail
echo '=== GIT / DEPLOY SHA ==='
cat /opt/siber/backups/*/previous-deploy-sha.txt 2>/dev/null | tail -3 || echo NO_PREVIOUS_SHA
ls -lt /opt/siber/backups/ 2>/dev/null | head -5
echo '=== DOCKER PS ==='
cd /opt/siber && docker compose -f docker-compose.prod.yml ps
echo '=== IMAGE LABELS api ==='
docker inspect siber-api --format '{{json .Config.Labels}}' 2>/dev/null || echo NO_LABELS
echo '=== ENV (non-secret keys) ==='
docker exec siber-api sh -c 'env | grep -E "^(ENVIRONMENT|DEBUG|SKIP_DOMAIN|ACCESS_TOKEN|REFRESH_TOKEN|AUTH_RATE|AUTH_REFRESH|AI_ENABLED|SMTP_ENABLED|NOTIFICATIONS|SCAN_DAILY|SCAN_CONCURRENCY|CORS_ORIGINS|TRUSTED_PROXY|PUBLIC_REGISTRATION|GIT_COMMIT|RELEASE_TAG|BUILD_)=" | sort' 2>/dev/null || true
echo '=== HEALTH ==='
curl -sf http://127.0.0.1:8010/api/v1/health | head -c 500; echo
curl -sf http://127.0.0.1:8010/api/v1/health/ready | head -c 500; echo
echo '=== PORTS (host) ==='
ss -lntp | grep -E ':8010|:3011|:5432|:6379|:8080' || true
echo '=== DISK/MEM ==='
df -h /opt/siber | tail -1
free -h | head -2
echo '=== BACKUP ==='
DUMP=/opt/siber/backups/20260723T124710Z/siber-pre-deploy.dump
if [ -f "$DUMP" ]; then ls -la "$DUMP"; sha256sum "$DUMP"; pg_restore --list "$DUMP" 2>/dev/null | head -5; else echo BACKUP_MISSING; fi
echo '=== ADMIN CHECK (exists only) ==='
docker exec siber-postgres psql -U siber -d siber -tAc "SELECT email, is_platform_admin, is_active FROM users WHERE email IN ('admin@admin.com') OR email LIKE '%pilot-sim%' OR email LIKE '%@example.com' LIMIT 20;" 2>/dev/null || true
echo '=== RESTART COUNTS ==='
docker inspect siber-api siber-worker siber-frontend --format '{{.Name}} restarts={{.RestartCount}}' 2>/dev/null
echo PRECHECK_DONE
`;

async function main() {
  if (!password) { console.error('DEPLOY_SSH_PASSWORD required'); process.exit(1); }
  const conn = new Client();
  await new Promise((resolve, reject) => {
    conn.on('ready', async () => {
      try {
        await exec(conn, cmd);
        conn.end();
        resolve();
      } catch (e) { conn.end(); reject(e); }
    });
    conn.on('error', reject);
    conn.connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 120000 });
  });
}

main().catch((e) => { console.error(e.message); process.exit(1); });
