const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
echo '=== DOCKER ==='
cd /opt/siber && docker compose -f docker-compose.prod.yml ps
curl -sS http://127.0.0.1:3011/ | head -c 150; echo
curl -sS -H 'Host: siber.cloudnira.com' http://127.0.0.1/ | head -c 150; echo
curl -sS -k -H 'Host: siber.cloudnira.com' https://127.0.0.1/ | head -c 150; echo
echo '=== SIBER NGINX ==='
grep -n '3011\\|8010\\|proxy' /etc/nginx/plesk.conf.d/vhosts/siber.cloudnira.com.conf | head -20
echo '=== SIBER APACHE ==='
cat /var/www/vhosts/system/siber.cloudnira.com/conf/vhost.conf
cat /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_ssl.conf
echo '=== SIBER NGINX CUSTOM ==='
cat /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_nginx.conf 2>/dev/null || echo none
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 60000 });
