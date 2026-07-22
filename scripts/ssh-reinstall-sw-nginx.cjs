const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
echo '=== DPKG LOCK ==='
ps aux | grep -E 'dpkg|apt' | grep -v grep || true
echo '=== PLESK NGINX ==='
dpkg -l | grep sw-nginx
which sw-nginx 2>/dev/null || true
ls -la /usr/sbin/nginx /opt/psa/admin/sbin/nginx 2>/dev/null || true
/usr/sbin/plesk version 2>/dev/null | head -3 || true
echo '=== WAIT FOR DPKG ==='
for i in 1 2 3 4 5 6 7 8 9 10; do
  if fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1; then
    echo "dpkg locked, wait $i"
    sleep 5
  else
    break
  fi
done
echo '=== REINSTALL SW-NGINX ==='
DEBIAN_FRONTEND=noninteractive apt-get install -y --reinstall sw-nginx 2>&1 | tail -40
echo '=== PLESK REPAIR WEB ==='
/usr/sbin/plesk repair web -y 2>&1 | tail -30
echo '=== NGINX TEST ==='
nginx -t 2>&1
echo '=== START SERVICES ==='
systemctl start nginx || true
systemctl restart apache2 || true
ss -lntp | grep -E ':80 |:443 ' || true
curl -sS -k https://siber.cloudnira.com/api/v1/health | head -c 200; echo
echo REPAIR_DONE
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 600000 });
