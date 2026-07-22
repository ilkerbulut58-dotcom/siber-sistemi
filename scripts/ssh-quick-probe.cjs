const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
echo '=== DPKG STATUS ==='
ps aux | grep dpkg | grep -v grep || echo 'no dpkg'
echo '=== PASSENGER FILES ==='
dpkg -L passenger 2>/dev/null | grep -E 'ngx_http|\.so' | head -20
dpkg -L passenger-dev 2>/dev/null | grep -E 'ngx_http|\.so' | head -20
find /usr/lib/passenger /usr/share/passenger -name '*.so' 2>/dev/null | head -20
echo '=== NGINX BIN ==='
nginx -V 2>&1 | head -3
ls -la /opt/psa/admin/sbin/nginx 2>/dev/null || true
echo '=== QUICK FIX: symlink module if found elsewhere ==='
MOD=$(find /usr -name 'ngx_http_passenger_module.so' 2>/dev/null | head -1)
if [ -n "$MOD" ]; then
  mkdir -p /usr/share/nginx/nginx/modules
  ln -sf "$MOD" /usr/share/nginx/nginx/modules/ngx_http_passenger_module.so
  echo "symlinked $MOD"
fi
ls -la /usr/share/nginx/nginx/modules/ 2>/dev/null || true
nginx -t 2>&1 | head -5
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 60000 });
