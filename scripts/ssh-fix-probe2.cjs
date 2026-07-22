const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
echo '=== APACHE STATUS ==='
systemctl status apache2 --no-pager | head -20
echo '=== NGINX STATUS ==='
systemctl status nginx --no-pager | head -20 2>/dev/null || true
echo '=== SW-CORE ==='
systemctl status sw-cp-server --no-pager | head -10 2>/dev/null || true
systemctl status sw-engine --no-pager | head -10 2>/dev/null || true
echo '=== ALL 80/443 ==='
ss -lntp | grep -E ':80 |:443 ' || echo 'NONE'
echo '=== PASSENGER CONF ==='
cat /etc/nginx/modules.conf.d/phusion-passenger.conf 2>/dev/null || true
echo '=== PLESK WEB SERVER ==='
plesk bin server_pref --show-web-server 2>/dev/null || true
plesk bin server_pref --show 2>/dev/null | grep -i nginx || true
echo '=== APACHE ERROR LOG TAIL ==='
tail -30 /var/log/apache2/error.log 2>/dev/null || tail -30 /var/log/httpd/error_log 2>/dev/null || true
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 60000 });
