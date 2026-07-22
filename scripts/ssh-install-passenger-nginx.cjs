const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
echo '=== APT SEARCH ==='
apt-cache search passenger | grep -i nginx || true
apt-cache search nginx | grep -i passenger || true
dpkg -l | grep -E 'nginx|passenger' | head -20
echo '=== TRY REINSTALL PASSENGER NGINX ==='
DEBIAN_FRONTEND=noninteractive apt-get install -y --reinstall libnginx-mod-http-passenger-plesk 2>&1 | tail -30 || \
DEBIAN_FRONTEND=noninteractive apt-get install -y libnginx-mod-http-passenger-plesk 2>&1 | tail -30 || \
DEBIAN_FRONTEND=noninteractive apt-get install -y --reinstall passenger 2>&1 | tail -20
echo '=== MODULE AFTER INSTALL ==='
find /usr -name 'ngx_http_passenger_module.so' 2>/dev/null
nginx -v 2>&1
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 300000 });
