const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
set -x
echo '=== STUCK PROCESSES ==='
ps aux | grep -E 'dpkg|apt-get|apt install' | grep -v grep || true

echo '=== UNLOCK DPKG IF STUCK ==='
if pgrep -x dpkg >/dev/null; then
  kill -9 $(pgrep -x dpkg) 2>/dev/null || true
fi
pkill -9 apt-get 2>/dev/null || true
pkill -9 apt 2>/dev/null || true
rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock
DEBIAN_FRONTEND=noninteractive dpkg --configure -a 2>&1 | tail -15 || true

echo '=== INSTALL SW-NGINX ==='
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -f
DEBIAN_FRONTEND=noninteractive apt-get install -y sw-nginx 2>&1 | tail -25

echo '=== RESTORE PASSENGER ==='
if [ -f /etc/nginx/conf.d/phusion-passenger.conf.disabled ]; then mv /etc/nginx/conf.d/phusion-passenger.conf.disabled /etc/nginx/conf.d/phusion-passenger.conf; fi
if [ ! -e /etc/nginx/modules.conf.d/phusion-passenger.conf ] && [ -f /etc/nginx/modules.available.d/phusion-passenger.load ]; then
  ln -sf ../modules.available.d/phusion-passenger.load /etc/nginx/modules.conf.d/phusion-passenger.conf
fi
find /usr -name 'ngx_http_passenger_module.so' 2>/dev/null | head -3

echo '=== NGINX TEST ==='
nginx -t 2>&1

echo '=== START ==='
systemctl enable nginx
systemctl restart nginx
systemctl restart apache2
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com
nginx -t && systemctl reload nginx

ss -lntp | grep -E ':80 |:443 '
curl -sS -k https://siber.cloudnira.com/api/v1/health; echo
echo WEBSTACK_OK
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
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 600000 });
