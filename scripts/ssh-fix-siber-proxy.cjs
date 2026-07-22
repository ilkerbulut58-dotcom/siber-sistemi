const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const nginxConf = `location /api/v1/ {
\tproxy_pass http://127.0.0.1:8010/api/v1/;
\tproxy_http_version 1.1;
\tproxy_set_header Host $host;
\tproxy_set_header X-Real-IP $remote_addr;
\tproxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
\tproxy_set_header X-Forwarded-Proto $scheme;
}

location / {
\tproxy_pass http://127.0.0.1:3011;
\tproxy_http_version 1.1;
\tproxy_set_header Upgrade $http_upgrade;
\tproxy_set_header Connection "upgrade";
\tproxy_set_header Host $host;
\tproxy_set_header X-Real-IP $remote_addr;
\tproxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
\tproxy_set_header X-Forwarded-Proto $scheme;
\tproxy_cache_bypass $http_upgrade;
}
`;

const cmd = `
set -e
cat > /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_nginx.conf << 'NGXEOF'
${nginxConf}
NGXEOF
chmod 600 /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_nginx.conf
/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com
nginx -t
systemctl reload nginx

curl -sS -k https://siber.cloudnira.com/api/v1/health; echo
curl -sS -k https://siber.cloudnira.com/ | grep -o '<title>[^<]*</title>' || true
echo FRONTEND_OK
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 60000 });
