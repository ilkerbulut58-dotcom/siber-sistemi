const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
echo '=== APACHE BACKEND TEST ==='
curl -sS -H 'Host: siber.cloudnira.com' http://127.0.0.1:7080/ | head -c 200; echo
curl -sS -k -H 'Host: siber.cloudnira.com' https://127.0.0.1:7081/ | head -c 200; echo
echo '=== APACHE ERROR LOG ==='
tail -20 /var/www/vhosts/system/siber.cloudnira.com/logs/error_log 2>/dev/null || tail -20 /var/www/vhosts/system/siber.cloudnira.com/logs/proxy_error_log 2>/dev/null || true
echo '=== NGINX PROXY ERROR ==='
tail -15 /var/www/vhosts/system/siber.cloudnira.com/logs/proxy_error_log 2>/dev/null || true
echo '=== APACHE MODULES ==='
apache2ctl -M 2>/dev/null | grep proxy || httpd -M 2>/dev/null | grep proxy || true
echo '=== HTTPDMNG RECONFIGURE ==='
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com
systemctl restart apache2
curl -sS -k https://siber.cloudnira.com/ | grep -o '<title>[^<]*</title>' || true
curl -sS -k https://siber.cloudnira.com/api/v1/health; echo
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 60000 });
