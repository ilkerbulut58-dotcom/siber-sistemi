const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a
echo DPKG_START
dpkg --configure -a
echo DPKG_DONE
apt-get update -qq
apt-get install -y sw-nginx
echo SW_NGINX_DONE
find /usr -name ngx_http_passenger_module.so 2>/dev/null
nginx -t
systemctl restart nginx
systemctl restart apache2
ss -lntp | grep -E ':80 |:443 '
curl -sS -k https://siber.cloudnira.com/api/v1/health
echo ALL_DONE
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 600000 });
