const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
set -e
echo '=== DISABLE PASSENGER NGINX MODULE LOAD ==='
rm -f /etc/nginx/modules.conf.d/phusion-passenger.conf
if [ -f /etc/nginx/conf.d/phusion-passenger.conf ]; then
  mv /etc/nginx/conf.d/phusion-passenger.conf /etc/nginx/conf.d/phusion-passenger.conf.off
fi

echo '=== COMMENT PASSENGER DIRECTIVES IN VHOSTS ==='
for f in /etc/nginx/plesk.conf.d/vhosts/*.conf; do
  if grep -q passenger "$f"; then
    cp "$f" "$f.bak-$(date +%s)"
    sed -i 's/^\\([[:space:]]*\\)passenger_/#\\1passenger_/g' "$f"
    echo "patched $f"
  fi
done

echo '=== NGINX TEST ==='
nginx -t

echo '=== START NGINX + APACHE ==='
systemctl enable nginx
systemctl restart nginx
systemctl restart apache2
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com
nginx -t && systemctl reload nginx

echo '=== PORTS ==='
ss -lntp | grep -E ':80 |:443 ' || true

echo '=== SIBER ==='
curl -sS -k https://siber.cloudnira.com/api/v1/health; echo
curl -sS -k https://siber.cloudnira.com/ | grep -o '<title>[^<]*</title>' || true

echo NGINX_BYPASS_OK
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
