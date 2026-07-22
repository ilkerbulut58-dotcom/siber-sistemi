const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
echo '=== PASSENGER ROOT ==='
passenger-config --root
passenger-config build-native-support 2>&1 | tail -5 || true
echo '=== SEARCH MODULE ==='
find /usr/share/passenger /opt/psa -name 'ngx_http_passenger_module.so' 2>/dev/null
find /usr -name 'ngx_http_passenger_module.so' 2>/dev/null
apt-cache search passenger nginx 2>/dev/null | head -10
dpkg -l | grep -i nginx | grep -i passenger || true
echo '=== PLESK BIN ==='
ls /usr/sbin/plesk /opt/psa/bin/plesk 2>/dev/null || true
echo '=== NGINX MODULES AVAILABLE ==='
ls -la /etc/nginx/modules.available.d/ 2>/dev/null || true
cat /etc/nginx/modules.available.d/phusion-passenger.load 2>/dev/null || true
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 120000 });
