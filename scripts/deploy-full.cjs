const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execSync } = require('child_process');
const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const host = '87.106.10.169';
const username = 'root';
const password = process.env.DEPLOY_SSH_PASSWORD;
const projectRoot = path.join(__dirname, '..');
const remoteRoot = '/opt/siber';
const archiveName = 'siber-deploy.tgz';
const archivePath = path.join(projectRoot, archiveName);

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
  console.log('Archive created:', archivePath, `(${Math.round(fs.statSync(archivePath).size / 1024)} KB)`);
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
      const remoteDir = path.posix.dirname(remotePath);
      sftp.mkdir(remoteDir, { mode: 0o755 }, () => {
        sftp.fastPut(localPath, remotePath, (e) => (e ? reject(e) : resolve()));
      });
    });
  });
}

async function main() {
  if (!password) {
    console.error('DEPLOY_SSH_PASSWORD required');
    process.exit(1);
  }

  buildArchive();

  const pgPass = crypto.randomBytes(18).toString('base64url');
  const secretKey = crypto.randomBytes(32).toString('hex');

  const remoteCmd = `
set -e
echo "=== CLEANUP OLD SIMPLE SETUP ==="
systemctl stop siber-api 2>/dev/null || true
systemctl disable siber-api 2>/dev/null || true
rm -f /etc/systemd/system/siber-api.service
systemctl daemon-reload
rm -rf /opt/siber-api
rm -f /var/www/vhosts/cloudnira.com/siber.cloudnira.com/index.html

echo "=== INSTALL DOCKER IF NEEDED ==="
if ! command -v docker >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  systemctl enable docker
  systemctl start docker
fi
docker --version
docker compose version

echo "=== EXTRACT PROJECT ==="
mkdir -p ${remoteRoot}
rm -rf ${remoteRoot}/backend ${remoteRoot}/frontend
tar -xzf ${remoteRoot}/${archiveName} -C ${remoteRoot}

if [ -f ${remoteRoot}/.env ]; then
  set -a
  . ${remoteRoot}/.env
  set +a
  pgPass="\${POSTGRES_PASSWORD:-${pgPass}}"
  secretKey="\${SECRET_KEY:-${secretKey}}"
  skipDomain="false"
  useCelery="true"
  zapEnabled="true"
  aiEnabled="\${AI_ENABLED:-false}"
  openAiKey="\${OPENAI_API_KEY:-}"
  accessExpire="\${ACCESS_TOKEN_EXPIRE_MINUTES:-480}"
  trustedProxyIps="\${TRUSTED_PROXY_IPS:-127.0.0.1}"
  rateLimitEnabled="\${RATE_LIMIT_ENABLED:-true}"
  authRateLimit="\${AUTH_RATE_LIMIT_PER_MINUTE:-10}"
  uploadRateLimit="\${UPLOAD_RATE_LIMIT_PER_HOUR:-20}"
  retestRateLimit="\${RETEST_RATE_LIMIT_PER_HOUR:-30}"
  mobileMaxUpload="\${MOBILE_MAX_UPLOAD_BYTES:-104857600}"
  mobileAnalysisTimeout="\${MOBILE_ANALYSIS_TIMEOUT_SECONDS:-600}"
  mobileAnalysisMemory="\${MOBILE_ANALYSIS_MEMORY_LIMIT:-768m}"
  mobileAnalysisCpus="\${MOBILE_ANALYSIS_CPUS:-1.0}"
  mobileAnalysisPids="\${MOBILE_ANALYSIS_PIDS_LIMIT:-128}"
  initialPlatformAdminEmail="\${INITIAL_PLATFORM_ADMIN_EMAIL:-}"
  initialPlatformAdminPassword="\${INITIAL_PLATFORM_ADMIN_PASSWORD:-}"
  echo "Reusing existing production secrets"
else
  pgPass="${pgPass}"
  secretKey="${secretKey}"
  skipDomain="false"
  useCelery="true"
  zapEnabled="true"
  aiEnabled="false"
  openAiKey=""
  accessExpire="480"
  trustedProxyIps="127.0.0.1"
  rateLimitEnabled="true"
  authRateLimit="10"
  uploadRateLimit="20"
  retestRateLimit="30"
  mobileMaxUpload="104857600"
  mobileAnalysisTimeout="600"
  mobileAnalysisMemory="768m"
  mobileAnalysisCpus="1.0"
  mobileAnalysisPids="128"
  initialPlatformAdminEmail=""
  initialPlatformAdminPassword=""
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
ACCESS_TOKEN_EXPIRE_MINUTES=\${accessExpire}
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=https://siber.cloudnira.com
NEXT_PUBLIC_API_URL=https://siber.cloudnira.com
SKIP_DOMAIN_VERIFICATION=false
USE_CELERY_FOR_SCANS=\${useCelery}
ZAP_API_URL=http://zap:8080
ZAP_ENABLED=\${zapEnabled}
AI_ENABLED=\${aiEnabled}
AI_PROVIDER=openai
OPENAI_API_KEY=\${openAiKey}
AI_MODEL=gpt-4o-mini
AI_BASE_URL=https://api.openai.com/v1
AI_TIMEOUT_SECONDS=30
TRUSTED_PROXY_IPS=\${trustedProxyIps}
RATE_LIMIT_ENABLED=\${rateLimitEnabled}
AUTH_RATE_LIMIT_PER_MINUTE=\${authRateLimit}
UPLOAD_RATE_LIMIT_PER_HOUR=\${uploadRateLimit}
RETEST_RATE_LIMIT_PER_HOUR=\${retestRateLimit}
MOBILE_MAX_UPLOAD_BYTES=\${mobileMaxUpload}
MOBILE_ANALYSIS_TIMEOUT_SECONDS=\${mobileAnalysisTimeout}
MOBILE_ANALYSIS_MEMORY_LIMIT=\${mobileAnalysisMemory}
MOBILE_ANALYSIS_CPUS=\${mobileAnalysisCpus}
MOBILE_ANALYSIS_PIDS=\${mobileAnalysisPids}
INITIAL_PLATFORM_ADMIN_EMAIL=\${initialPlatformAdminEmail}
INITIAL_PLATFORM_ADMIN_PASSWORD=\${initialPlatformAdminPassword}
ENVEOF
chmod 600 ${remoteRoot}/.env

echo "=== DOCKER BUILD & START ==="
cd ${remoteRoot}
docker compose -f docker-compose.prod.yml up -d --build

echo "=== WAIT FOR API ==="
for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1:8010/api/v1/health >/dev/null; then echo "API up"; break; fi
  sleep 3
  if [ "$i" -eq 60 ]; then echo "API timeout"; exit 1; fi
done

echo "=== SYNC POSTGRES PASSWORD ==="
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U siber -d siber -c "ALTER USER siber WITH PASSWORD '\${pgPass}';"

echo "=== MIGRATIONS ==="
docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head

echo "=== BOOTSTRAP ADMIN ==="
if [ -n "\${initialPlatformAdminEmail}" ] && [ -n "\${initialPlatformAdminPassword}" ]; then
  docker compose -f docker-compose.prod.yml exec -T \
    -e INITIAL_PLATFORM_ADMIN_EMAIL="\${initialPlatformAdminEmail}" \
    -e INITIAL_PLATFORM_ADMIN_PASSWORD="\${initialPlatformAdminPassword}" \
    api python scripts/create_admin.py
else
  echo "Skipped: initial platform-admin credentials are not configured."
fi

echo "=== NGINX PROXY ==="
cat > /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_nginx.conf << 'NGXEOF'
${nginxConf}
NGXEOF
cat > /var/www/vhosts/system/siber.cloudnira.com/conf/vhost.conf << 'APACHEEOF'
<IfModule mod_proxy.c>
ProxyPreserveHost On
ProxyPass /api/v1 http://127.0.0.1:8010/api/v1
ProxyPassReverse /api/v1 http://127.0.0.1:8010/api/v1
ProxyPass / http://127.0.0.1:3011/
ProxyPassReverse / http://127.0.0.1:3011/
</IfModule>
APACHEEOF
cat > /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_ssl.conf << 'APACHEEOF'
<IfModule mod_proxy.c>
ProxyPreserveHost On
ProxyPass /api/v1 http://127.0.0.1:8010/api/v1
ProxyPassReverse /api/v1 http://127.0.0.1:8010/api/v1
ProxyPass / http://127.0.0.1:3011/
ProxyPassReverse / http://127.0.0.1:3011/
</IfModule>
APACHEEOF
chmod 600 /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_nginx.conf /var/www/vhosts/system/siber.cloudnira.com/conf/vhost.conf /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_ssl.conf
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com
nginx -t && systemctl reload nginx

echo "=== SMOKE TESTS ==="
curl -sS http://127.0.0.1:8010/api/v1/health | head -c 200; echo
curl -sS http://127.0.0.1:3011/ | head -c 120; echo
curl -sS https://siber.cloudnira.com/api/v1/health -k | head -c 200; echo
curl -sS https://siber.cloudnira.com/api/v1/health/ready -k | head -c 300; echo
curl -sS https://siber.cloudnira.com/ -k | grep -o '<title>[^<]*</title>' || true

echo FULL_DEPLOY_OK
`;

  const conn = new Client();
  await new Promise((resolve, reject) => {
    conn.on('ready', async () => {
      try {
        console.log('Uploading archive...');
        await upload(conn, archivePath, `${remoteRoot}/${archiveName}`);
        console.log('Running remote setup (this may take several minutes)...');
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
  console.log('Deploy complete.');
}

main().catch((e) => {
  console.error('Deploy failed:', e.message);
  process.exit(1);
});
