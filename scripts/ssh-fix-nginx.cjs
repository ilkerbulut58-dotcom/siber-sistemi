const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
set -e
echo '=== DISABLE BROKEN PASSENGER NGINX CONFIGS ==='
for f in /etc/nginx/modules.conf.d/phusion-passenger.conf /etc/nginx/conf.d/phusion-passenger.conf; do
  if [ -e "$f" ] && [ ! -f "$f.disabled" ]; then
    mv "$f" "$f.disabled"
    echo "disabled $f"
  fi
done
# remove symlink if still present
rm -f /etc/nginx/modules.conf.d/phusion-passenger.conf 2>/dev/null || true

echo '=== NGINX TEST ==='
nginx -t

echo '=== START NGINX ==='
systemctl enable nginx || true
systemctl start nginx
systemctl is-active nginx

echo '=== RESTART APACHE ==='
apache2ctl configtest
systemctl restart apache2

echo '=== RECONFIGURE SIBER ONLY ==='
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com
nginx -t && systemctl reload nginx

echo '=== PORTS AFTER FIX ==='
ss -lntp | grep -E ':80 |:443 ' || true

echo '=== SIBER TESTS ==='
curl -sS -k https://siber.cloudnira.com/api/v1/health | head -c 220; echo
curl -sS -k https://siber.cloudnira.com/ | grep -o '<title>[^<]*</title>' || true

echo FIX_OK
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
