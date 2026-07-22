const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
grep -n 'location\\|proxy_pass\\|7080\\|7081\\|3011' /etc/nginx/plesk.conf.d/vhosts/siber.cloudnira.com.conf
echo '---'
cat /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_nginx.conf
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 60000 });
