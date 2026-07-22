const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
echo '=== KILL PID 3797 CHAIN ==='
ps -ef | grep -E '3797|needrestart|dpkg-status' | grep -v grep || true
kill -9 3797 3799 3800 3801 3260 3262 3263 3264 2>/dev/null || true
sleep 2
rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock
echo '=== DPKG ==='
dpkg --configure -a 2>&1 | tail -25
echo '=== INSTALL SW-NGINX ==='
apt-get update -qq
apt-get install -y sw-nginx 2>&1 | tail -30
echo '=== RESTORE PASSENGER LINK ==='
ln -sf ../modules.available.d/phusion-passenger.load /etc/nginx/modules.conf.d/phusion-passenger.conf 2>/dev/null || true
if [ -f /etc/nginx/conf.d/phusion-passenger.conf.disabled ]; then mv /etc/nginx/conf.d/phusion-passenger.conf.disabled /etc/nginx/conf.d/phusion-passenger.conf; fi
find /usr -name ngx_http_passenger_module.so 2>/dev/null
nginx -t 2>&1
systemctl restart nginx
systemctl restart apache2
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com
nginx -t && systemctl reload nginx
ss -lntp | grep -E ':80 |:443 '
curl -sS -k https://siber.cloudnira.com/api/v1/health; echo
curl -sS -k https://siber.cloudnira.com/ | grep -o '<title>[^<]*</title>' || true
echo ALL_DONE
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 600000 });
