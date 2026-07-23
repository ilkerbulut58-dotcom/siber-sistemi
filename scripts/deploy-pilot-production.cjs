/**
 * Production pilot deploy for siber.cloudnira.com
 *
 * Requires:
 *   DEPLOY_SSH_PASSWORD — root SSH password (never commit)
 *   DEPLOY_CONFIRM=production-pilot — explicit operator confirmation
 *
 * Does NOT run seed_closed_pilot_simulation or insert simulation users.
 */
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const host = '87.106.10.169';
const username = 'root';
const password = process.env.DEPLOY_SSH_PASSWORD;
const domain = 'siber.cloudnira.com';
const projectRoot = path.join(__dirname, '..');
const remoteRoot = '/opt/siber';
const archiveName = 'siber-deploy.tgz';
const archivePath = path.join(projectRoot, archiveName);
const deploySha = execSync('git rev-parse HEAD', { cwd: projectRoot, encoding: 'utf8' }).trim();

const nginxConf = `location /api/v1/ {
\tproxy_pass http://127.0.0.1:8010/api/v1/;
\tproxy_http_version 1.1;
\tproxy_set_header Host $host;
\tproxy_set_header X-Real-IP $remote_addr;
\tproxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
\tproxy_set_header X-Forwarded-Proto $scheme;
}
`;

function buildArchive() {
  if (fs.existsSync(archivePath)) fs.unlinkSync(archivePath);
  const excludes = [
    '--exclude=backend/.venv',
    '--exclude=backend/__pycache__',
    '--exclude=backend/.pytest_cache',
    '--exclude=backend/.ruff_cache',
    '--exclude=frontend/node_modules',
    '--exclude=frontend/.next',
    '--exclude=deploy/simple-setup',
    '--exclude=scripts/ssh-probe',
    '--exclude=*.tgz',
    '--exclude=.git',
    '--exclude=.env',
  ].join(' ');
  const cmd = `tar -czf "${archiveName}" ${excludes} -C "${projectRoot}" backend frontend docker-compose.prod.yml deploy/production.env.example README.md`;
  execSync(cmd, { cwd: projectRoot, stdio: 'inherit' });
  console.log('Archive:', archivePath, `(${Math.round(fs.statSync(archivePath).size / 1024)} KB)`);
  console.log('Deploy SHA:', deploySha);
}

function exec(conn, cmd) {
  return new Promise((resolve, reject) => {
    conn.exec(cmd, (err, stream) => {
      if (err) return reject(err);
      stream.on('data', (d) => process.stdout.write(d));
      stream.stderr.on('data', (d) => process.stderr.write(d));
      stream.on('close', (code) => (code === 0 ? resolve() : reject(new Error(`Remote exit ${code}`))));
    });
  });
}

function upload(conn, localPath, remotePath) {
  return new Promise((resolve, reject) => {
    conn.sftp((err, sftp) => {
      if (err) return reject(err);
      sftp.fastPut(localPath, remotePath, (e) => (e ? reject(e) : resolve()));
    });
  });
}

async function main() {
  if (!password) {
    console.error('DEPLOY_SSH_PASSWORD required');
    process.exit(1);
  }
  if (process.env.DEPLOY_CONFIRM !== 'production-pilot') {
    console.error('Set DEPLOY_CONFIRM=production-pilot to acknowledge production pilot deploy');
    process.exit(1);
  }

  buildArchive();

  const remoteCmd = `
set -euo pipefail
TS=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_DIR=${remoteRoot}/backups/\${TS}
mkdir -p "$BACKUP_DIR"

echo "=== PRE-DEPLOY INVENTORY ==="
docker --version
docker compose version
df -h ${remoteRoot} || df -h /
cd ${remoteRoot} 2>/dev/null && docker compose -f docker-compose.prod.yml ps || echo "No existing stack"
if [ -f ${remoteRoot}/.env ]; then
  echo "Existing .env present (secrets preserved)"
  grep -E '^(ENVIRONMENT|SKIP_DOMAIN_VERIFICATION|USE_CELERY)' ${remoteRoot}/.env || true
fi

echo "=== POSTGRES BACKUP (required before migration) ==="
cd ${remoteRoot}
if docker compose -f docker-compose.prod.yml ps postgres 2>/dev/null | grep -q Up; then
  docker compose -f docker-compose.prod.yml exec -T postgres \\
    pg_dump -U siber -d siber -Fc > "$BACKUP_DIR/siber-pre-deploy.dump"
  test -s "$BACKUP_DIR/siber-pre-deploy.dump"
  ls -lh "$BACKUP_DIR/siber-pre-deploy.dump"
  echo "BACKUP_OK size=$(stat -c%s "$BACKUP_DIR/siber-pre-deploy.dump")"
else
  echo "No running postgres — fresh deploy path"
  touch "$BACKUP_DIR/siber-pre-deploy.dump"
fi

echo "=== RECORD PRE-MIGRATION REVISION ==="
PRE_REV=""
if docker compose -f docker-compose.prod.yml ps api 2>/dev/null | grep -q Up; then
  PRE_REV=$(docker compose -f docker-compose.prod.yml exec -T api alembic current 2>/dev/null | tail -1 || true)
fi
echo "$PRE_REV" > "$BACKUP_DIR/alembic-pre.txt"
echo "PRE_REVISION=$PRE_REV"

echo "=== EXTRACT NEW RELEASE ${deploySha} ==="
mkdir -p ${remoteRoot}
tar -xzf ${remoteRoot}/${archiveName} -C ${remoteRoot}
echo "${deploySha}" > "$BACKUP_DIR/previous-deploy-sha.txt"

if [ -f ${remoteRoot}/.env ]; then
  set -a
  . ${remoteRoot}/.env
  set +a
  pgPass="\${POSTGRES_PASSWORD}"
  secretKey="\${SECRET_KEY}"
  initialPlatformAdminEmail="\${INITIAL_PLATFORM_ADMIN_EMAIL:-}"
  initialPlatformAdminPassword="\${INITIAL_PLATFORM_ADMIN_PASSWORD:-}"
  openAiKey="\${OPENAI_API_KEY:-}"
  aiEnabled="\${AI_ENABLED:-false}"
  echo "Reusing existing production secrets"
else
  echo "ERROR: ${remoteRoot}/.env missing — create from deploy/production.env.example first"
  exit 1
fi

cat > ${remoteRoot}/.env << ENVEOF
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
POSTGRES_USER=siber
POSTGRES_PASSWORD=\${pgPass}
POSTGRES_DB=siber
SECRET_KEY=\${secretKey}
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=https://${domain}
NEXT_PUBLIC_API_URL=https://${domain}
SKIP_DOMAIN_VERIFICATION=false
USE_CELERY_FOR_SCANS=true
ZAP_API_URL=http://zap:8080
ZAP_ENABLED=true
AI_ENABLED=\${aiEnabled}
AI_PROVIDER=openai
OPENAI_API_KEY=\${openAiKey}
AI_MODEL=gpt-4o-mini
AI_BASE_URL=https://api.openai.com/v1
AI_TIMEOUT_SECONDS=30
TRUSTED_PROXY_IPS=127.0.0.1
RATE_LIMIT_ENABLED=true
AUTH_RATE_LIMIT_PER_MINUTE=10
UPLOAD_RATE_LIMIT_PER_HOUR=20
RETEST_RATE_LIMIT_PER_HOUR=30
SCAN_RATE_LIMIT_PER_HOUR=10
SCAN_CONCURRENCY_LIMIT=1
SCAN_DAILY_QUOTA=5
NOTIFICATIONS_PROVIDER=noop
MOBILE_MAX_UPLOAD_BYTES=104857600
MOBILE_ANALYSIS_TIMEOUT_SECONDS=600
MOBILE_ANALYSIS_MEMORY_LIMIT=768m
MOBILE_ANALYSIS_CPUS=1.0
MOBILE_ANALYSIS_PIDS_LIMIT=128
INITIAL_PLATFORM_ADMIN_EMAIL=\${initialPlatformAdminEmail}
INITIAL_PLATFORM_ADMIN_PASSWORD=\${initialPlatformAdminPassword}
ENVEOF
chmod 600 ${remoteRoot}/.env

echo "=== DOCKER BUILD & ROLLING START ==="
cd ${remoteRoot}
docker compose -f docker-compose.prod.yml up -d --build

echo "=== WAIT FOR API ==="
for i in $(seq 1 90); do
  if curl -sf http://127.0.0.1:8010/api/v1/health >/dev/null; then echo "API up"; break; fi
  sleep 3
  if [ "$i" -eq 90 ]; then echo "API timeout"; exit 1; fi
done

echo "=== SYNC POSTGRES PASSWORD ==="
docker compose -f docker-compose.prod.yml exec -T postgres \\
  psql -U siber -d siber -c "ALTER USER siber WITH PASSWORD '\${pgPass}';"

echo "=== MIGRATIONS ==="
docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head
POST_REV=$(docker compose -f docker-compose.prod.yml exec -T api alembic current | tail -1)
echo "$POST_REV" > "$BACKUP_DIR/alembic-post.txt"
echo "POST_REVISION=$POST_REV"

echo "=== BOOTSTRAP PLATFORM ADMIN (if configured) ==="
if [ -n "\${initialPlatformAdminEmail}" ] && [ -n "\${initialPlatformAdminPassword}" ]; then
  docker compose -f docker-compose.prod.yml exec -T \\
    -e INITIAL_PLATFORM_ADMIN_EMAIL="\${initialPlatformAdminEmail}" \\
    -e INITIAL_PLATFORM_ADMIN_PASSWORD="\${initialPlatformAdminPassword}" \\
    api python scripts/create_admin.py
else
  echo "Skipped admin bootstrap — credentials not in .env"
fi

echo "=== NGINX / APACHE PROXY ==="
cat > /var/www/vhosts/system/${domain}/conf/vhost_nginx.conf << 'NGXEOF'
${nginxConf}
NGXEOF
cat > /var/www/vhosts/system/${domain}/conf/vhost.conf << 'APACHEEOF'
<IfModule mod_proxy.c>
ProxyPreserveHost On
ProxyPass /api/v1 http://127.0.0.1:8010/api/v1
ProxyPassReverse /api/v1 http://127.0.0.1:8010/api/v1
ProxyPass / http://127.0.0.1:3011/
ProxyPassReverse / http://127.0.0.1:3011/
</IfModule>
APACHEEOF
cat > /var/www/vhosts/system/${domain}/conf/vhost_ssl.conf << 'APACHEEOF'
<IfModule mod_proxy.c>
ProxyPreserveHost On
ProxyPass /api/v1 http://127.0.0.1:8010/api/v1
ProxyPassReverse /api/v1 http://127.0.0.1:8010/api/v1
ProxyPass / http://127.0.0.1:3011/
ProxyPassReverse / http://127.0.0.1:3011/
</IfModule>
APACHEEOF
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain ${domain} || true
nginx -t && systemctl reload nginx

echo "=== POST-DEPLOY SMOKE ==="
curl -sS http://127.0.0.1:8010/api/v1/health | head -c 300; echo
curl -sS http://127.0.0.1:8010/api/v1/health/ready | head -c 400; echo
curl -sS https://${domain}/api/v1/health -k | head -c 300; echo
curl -sS https://${domain}/api/v1/health/ready -k | head -c 400; echo
docker compose -f docker-compose.prod.yml ps

echo "BACKUP_DIR=\$BACKUP_DIR"
echo "DEPLOY_SHA=${deploySha}"
echo PILOT_PRODUCTION_DEPLOY_OK
`;

  const conn = new Client();
  await new Promise((resolve, reject) => {
    conn.on('ready', async () => {
      try {
        console.log('Uploading archive...');
        await upload(conn, archivePath, `${remoteRoot}/${archiveName}`);
        console.log('Running remote pilot production deploy...');
        await exec(conn, remoteCmd);
        conn.end();
        resolve();
      } catch (e) {
        conn.end();
        reject(e);
      }
    });
    conn.on('error', reject);
    conn.connect({ host, port: 22, username, password, readyTimeout: 120000 });
  });

  fs.unlinkSync(archivePath);
  console.log('Pilot production deploy finished.');
}

main().catch((e) => {
  console.error('Deploy failed:', e.message);
  process.exit(1);
});
