const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
set -e
TB=/var/www/vhosts/system/turbridge.de/conf/vhost_nginx.conf
echo '=== TURBRIDGE NGINX CONF (lines 35-50) ==='
nl -ba "$TB" | sed -n '35,50p'

echo '=== FIX DUPLICATE server_tokens ==='
cp "$TB" "$TB.bak-siber-fix"
awk '
  /server_tokens/ {
    if (seen++) { next }
  }
  { print }
' "$TB.bak-siber-fix" > "$TB"

echo '=== AFTER FIX ==='
nl -ba "$TB" | sed -n '35,50p'

echo '=== NGINX TEST ==='
nginx -t

echo '=== START ==='
systemctl restart nginx
systemctl restart apache2
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com
nginx -t && systemctl reload nginx

ss -lntp | grep -E ':80 |:443 '
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
