/**
 * Install single-server guardrails on production:
 * - /opt/siber/scripts/server/*.sh
 * - systemd: siber-web-recover.service (boot)
 * - cron: healthcheck every 5 minutes
 *
 * Requires DEPLOY_SSH_PASSWORD
 */
const fs = require('fs');
const path = require('path');
const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const host = '87.106.10.169';
const username = 'root';
const password = process.env.DEPLOY_SSH_PASSWORD;
const serverDir = path.join(__dirname, 'server');
const remoteDir = '/opt/siber/scripts/server';

const scriptFiles = ['lib.sh', 'web-stack-recover.sh', 'web-stack-healthcheck.sh', 'safe-vhost-reload.sh'];

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

  const conn = new Client();
  await new Promise((resolve, reject) => {
    conn.on('ready', async () => {
      try {
        console.log('=== Upload server guardrail scripts ===');
        await exec(conn, `mkdir -p ${remoteDir}`);
        for (const file of scriptFiles) {
          const local = path.join(serverDir, file);
          const remote = `${remoteDir}/${file}`;
          await upload(conn, local, remote);
          console.log('Uploaded', file);
        }

        const installCmd = `
set -e
# Fix Windows CRLF if scripts were uploaded from dev machine
for f in ${remoteDir}/*.sh; do sed -i 's/\\r$//' "$f"; done
chmod +x ${remoteDir}/*.sh

echo '=== systemd unit ==='
cat > /etc/systemd/system/siber-web-recover.service << 'UNITEOF'
[Unit]
Description=SIBER single-server web stack recovery after boot
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=${remoteDir}/web-stack-recover.sh boot
RemainAfterExit=yes
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
UNITEOF

systemctl daemon-reload
systemctl enable siber-web-recover.service

echo '=== cron healthcheck ==='
cat > /etc/cron.d/siber-web-guard << 'CRONEOF'
# SIBER single-server guard: auto-recover if apache/nginx/443/apps fail
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
*/5 * * * * root ${remoteDir}/web-stack-healthcheck.sh >> /var/log/siber-web-guard.log 2>&1
CRONEOF
chmod 644 /etc/cron.d/siber-web-guard
touch /var/log/siber-web-guard.log

echo '=== enable boot services ==='
systemctl enable apache2 nginx docker

echo '=== run healthcheck now ==='
${remoteDir}/web-stack-healthcheck.sh

echo '=== smoke ==='
curl -sS -k -o /dev/null -w 'siber %{http_code}\\n' https://siber.cloudnira.com/api/v1/health
curl -sS -k -o /dev/null -w 'turbridge %{http_code}\\n' https://turbridge.de/
curl -sS -k -o /dev/null -w 'cloudnira %{http_code}\\n' https://cloudnira.com/
systemctl is-enabled siber-web-recover.service
systemctl is-enabled apache2 nginx docker
grep siber-web-guard /etc/cron.d/siber-web-guard

echo GUARDRAILS_INSTALL_OK
`;
        await exec(conn, installCmd);
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

  console.log('Guardrails installed.');
}

main().catch((e) => {
  console.error('Install failed:', e.message);
  process.exit(1);
});
