const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
set -e
echo '=== WAIT DPKG (up to 5 min) ==='
for i in $(seq 1 60); do
  if fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; then
    echo "waiting dpkg... $i"
    sleep 5
  else
    break
  fi
done

echo '=== DPKG CONFIGURE ==='
DEBIAN_FRONTEND=noninteractive dpkg --configure -a 2>&1 | tail -20 || true

echo '=== INSTALL SW-NGINX ==='
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y sw-nginx 2>&1 | tail -30

echo '=== RESTORE PASSENGER CONFIGS ==='
for f in /etc/nginx/modules.conf.d/phusion-passenger.conf.disabled /etc/nginx/conf.d/phusion-passenger.conf.disabled; do
  if [ -f "$f" ]; then
    orig="\${f%.disabled}"
    mv "$f" "$orig"
    echo "restored $orig"
  fi
done
if [ ! -e /etc/nginx/modules.conf.d/phusion-passenger.conf ] && [ -f /etc/nginx/modules.available.d/phusion-passenger.load ]; then
  ln -sf ../modules.available.d/phusion-passenger.load /etc/nginx/modules.conf.d/phusion-passenger.conf
fi

echo '=== FIND MODULE ==='
find /usr -name 'ngx_http_passenger_module.so' 2>/dev/null | head -5
ls -la /usr/share/nginx/nginx/modules/ 2>/dev/null || true

echo '=== NGINX TEST ==='
nginx -t

echo '=== START WEB STACK ==='
systemctl enable nginx
systemctl restart nginx
systemctl restart apache2
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com
nginx -t && systemctl reload nginx

echo '=== PORTS ==='
ss -lntp | grep -E ':80 |:443 ' || true

echo '=== SIBER CHECK ==='
curl -sS -k https://siber.cloudnira.com/api/v1/health | head -c 220; echo
curl -sS -k https://siber.cloudnira.com/ | grep -o '<title>[^<]*</title>' || true

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
