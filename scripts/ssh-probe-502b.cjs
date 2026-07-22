const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
grep -n 'proxy_pass' /etc/nginx/plesk.conf.d/vhosts/siber.cloudnira.com.conf
echo '=== LOCAL TESTS ==='
curl -sS http://127.0.0.1:3011/ -o /dev/null -w '3011:%{http_code}\\n'
curl -sS -k -H 'Host: siber.cloudnira.com' https://127.0.0.1/ -o /dev/null -w 'nginx:%{http_code}\\n'
curl -sS -k https://siber.cloudnira.com/ -o /dev/null -w 'public:%{http_code}\\n'
tail -5 /var/www/vhosts/system/siber.cloudnira.com/logs/proxy_error_log
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 60000 });
