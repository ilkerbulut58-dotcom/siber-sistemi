const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
if (!password) {
  console.error('DEPLOY_SSH_PASSWORD required');
  process.exit(1);
}

const cmd = `
set -e
echo '=== SERVICES ==='
systemctl is-active nginx apache2 httpd 2>/dev/null || true
echo '=== PORTS ==='
ss -lntp | grep -E ':80|:443|:8010|:3011' || true
echo '=== LOCAL HEALTH ==='
curl -sS http://127.0.0.1:8010/api/v1/health || true
echo
curl -sS http://127.0.0.1:3011/ | head -c 120 || true
echo
echo '=== NGINX TEST ==='
nginx -t 2>&1 || true
echo '=== APACHE TEST ==='
apache2ctl configtest 2>&1 || httpd -t 2>&1 || true
echo '=== SIBER VHOST ==='
grep -n 'ProxyPass\\|8010\\|3011' /var/www/vhosts/system/siber.cloudnira.com/conf/vhost.conf 2>/dev/null || true
grep -n 'ProxyPass\\|8010\\|3011' /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_ssl.conf 2>/dev/null || true
echo '=== DOCKER ==='
cd /opt/siber && docker compose -f docker-compose.prod.yml ps
echo '=== TURBRIDGE CHECK (read only) ==='
grep -l turbridge /var/www/vhosts/system/*/conf/*.conf 2>/dev/null | head -5 || true
`;

const conn = new Client();
conn
  .on('ready', () => {
    conn.exec(cmd, (err, stream) => {
      if (err) {
        console.error(err.message);
        process.exit(1);
      }
      stream.on('data', (d) => process.stdout.write(d));
      stream.stderr.on('data', (d) => process.stderr.write(d));
      stream.on('close', (code) => {
        conn.end();
        process.exit(code || 0);
      });
    });
  })
  .on('error', (e) => {
    console.error(e.message);
    process.exit(1);
  })
  .connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 60000 });
