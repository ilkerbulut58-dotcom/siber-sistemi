const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
echo '=== FIND PASSENGER ==='
find /opt /usr/lib -name '*passenger*module*.so' 2>/dev/null | head -20
dpkg -l | grep -i passenger | head -10
which passenger-config 2>/dev/null || true
passenger-config --root 2>/dev/null || true
ls -la /usr/lib/nginx/modules/ 2>/dev/null || true
echo '=== TRY PLESK REPAIR WEB ==='
/usr/local/psa/admin/sbin/plesk repair web -y 2>&1 | tail -40
echo '=== NGINX TEST AFTER REPAIR ==='
nginx -t 2>&1 || true
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 300000 });
