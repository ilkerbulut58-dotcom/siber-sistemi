const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
grep -n server_tokens /var/www/vhosts/system/turbridge.de/conf/nginx.conf || true
grep -n server_tokens /etc/nginx/plesk.conf.d/vhosts/turbridge.de.conf || true
echo '--- nginx.conf tail ---'
tail -30 /var/www/vhosts/system/turbridge.de/conf/nginx.conf 2>/dev/null || true
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 60000 });
