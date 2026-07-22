const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
echo '=== FIND .so IN PASSENGER ==='
find /usr/lib/x86_64-linux-gnu/passenger -name '*.so' 2>/dev/null
ls -la /usr/lib/x86_64-linux-gnu/passenger/nginx_dynamic/ 2>/dev/null || true

echo '=== KILL STUCK DPKG/NEEDRESTART ==='
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
pkill -9 -f needrestart 2>/dev/null || true
pkill -9 -f dpkg-status 2>/dev/null || true
pkill -9 dpkg 2>/dev/null || true
pkill -9 apt-get 2>/dev/null || true
pkill -9 apt 2>/dev/null || true
sleep 2
rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock

echo '=== DPKG CONFIGURE ==='
dpkg --configure -a 2>&1 | tail -20

echo '=== INSTALL SW-NGINX ==='
apt-get update -qq
apt-get install -y sw-nginx 2>&1 | tail -25

echo '=== MODULE CHECK ==='
find /usr -name 'ngx_http_passenger_module.so' 2>/dev/null
nginx -t 2>&1 | head -8

echo '=== START NGINX ==='
systemctl restart nginx
ss -lntp | grep -E ':80 |:443 '
curl -sS -k https://siber.cloudnira.com/api/v1/health; echo
echo DONE
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 600000 });
