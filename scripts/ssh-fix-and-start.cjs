const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
set -e
TB=/var/www/vhosts/system/turbridge.de/conf/vhost_nginx.conf
cp "$TB" "$TB.bak-siber2"
# Remove duplicate server_tokens block (already set in nginx.conf)
sed -i '/turbridge-header-hardening-v2/,/server_tokens off;/d' "$TB"
echo '=== FIXED vhost_nginx.conf tail ==='
tail -8 "$TB"

nginx -t
systemctl restart nginx
systemctl restart apache2
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com
nginx -t && systemctl reload nginx

ss -lntp | grep -E ':80 |:443 '
echo '=== SIBER ==='
curl -sS -k https://siber.cloudnira.com/api/v1/health; echo
curl -sS -k https://siber.cloudnira.com/ | grep -o '<title>[^<]*</title>' || true
echo SITE_UP
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', (code) => {
      conn.end();
      process.exit(code || 0);
    });
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 120000 });
