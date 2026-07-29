/** Post-deploy smoke via SSH (register 403, env keys). */
const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');
const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
set -euo pipefail
echo '=== PUBLIC REGISTRATION ==='
curl -s -w '\\nHTTP=%{http_code}\\n' -X POST http://127.0.0.1:8010/api/v1/auth/register \\
  -H 'Content-Type: application/json' \\
  -d '{"email":"expert-probe-blocked@example.com","password":"SecurePass123!","full_name":"Probe"}' | head -c 400; echo
echo '=== ENV KEYS ==='
docker exec siber-api sh -c 'env | grep -E "^(PUBLIC_REGISTRATION|NOTIFICATIONS|SKIP_DOMAIN|ACCESS_TOKEN|SCAN_DAILY|SCAN_CONCURRENCY|PUBLIC_REGISTRATION)=" | sort'
echo '=== WORKER HEALTH (after wait) ==='
sleep 15
docker compose -f /opt/siber/docker-compose.prod.yml ps worker mobile-worker
echo '=== ADMIN STATUS ==='
docker exec siber-postgres psql -U siber -d siber -tAc "SELECT email,is_active,is_platform_admin FROM users WHERE email='admin@admin.com';"
echo SMOKE_OK
`;
async function main() {
  if (!password) { console.error('DEPLOY_SSH_PASSWORD required'); process.exit(1); }
  const conn = new Client();
  await new Promise((resolve, reject) => {
    conn.on('ready', () => {
      conn.exec(cmd, (err, stream) => {
        if (err) return reject(err);
        let out = '';
        stream.on('data', (d) => { out += d.toString(); process.stdout.write(d); });
        stream.stderr.on('data', (d) => process.stderr.write(d));
        stream.on('close', (code) => {
          conn.end();
          if (code !== 0) return reject(new Error(`exit ${code}`));
          if (!out.includes('HTTP=403')) return reject(new Error('register did not return 403'));
          resolve();
        });
      });
    });
    conn.on('error', reject);
    conn.connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 120000 });
  });
}
main().catch((e) => { console.error(e.message); process.exit(1); });
