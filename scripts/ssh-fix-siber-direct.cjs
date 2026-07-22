const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const cmd = `
set -e
NGX=/etc/nginx/plesk.conf.d/vhosts/siber.cloudnira.com.conf
cp "$NGX" "$NGX.bak-siber-proxy"

# Restore custom nginx: API only (no duplicate location /)
cat > /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_nginx.conf << 'NGXEOF'
location /api/v1/ {
	proxy_pass http://127.0.0.1:8010/api/v1/;
	proxy_http_version 1.1;
	proxy_set_header Host $host;
	proxy_set_header X-Real-IP $remote_addr;
	proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
	proxy_set_header X-Forwarded-Proto $scheme;
}
NGXEOF
chmod 600 /var/www/vhosts/system/siber.cloudnira.com/conf/vhost_nginx.conf

/usr/local/psa/admin/sbin/httpdmng --reconfigure-domain siber.cloudnira.com

# Point nginx directly to Docker frontend (bypass broken apache SSL upstream)
sed -i 's|proxy_pass "https://127.0.0.1:7081"|proxy_pass "http://127.0.0.1:3011"|g' "$NGX"
sed -i 's|proxy_pass "http://127.0.0.1:7080"|proxy_pass "http://127.0.0.1:3011"|g' "$NGX"
sed -i '/proxy_ssl_server_name/d; /proxy_ssl_name/d; /proxy_ssl_session_reuse/d' "$NGX"

nginx -t
systemctl reload nginx

curl -sS -k https://siber.cloudnira.com/api/v1/health; echo
curl -sS -k https://siber.cloudnira.com/ | grep -o '<title>[^<]*</title>' || true
echo SIBER_LIVE
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', () => conn.end());
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 60000 });
