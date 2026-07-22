const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const domainId = process.argv[2];
if (!domainId) {
  console.error('Usage: node verify-domain-ssh.cjs <domain-id>');
  process.exit(1);
}

const password = process.env.DEPLOY_SSH_PASSWORD;
if (!password) {
  console.error('DEPLOY_SSH_PASSWORD required');
  process.exit(1);
}

const sql = `UPDATE domains SET is_verified=true, verified_at=NOW() WHERE id='${domainId}';`;
const cmd = `docker compose -f /opt/siber/docker-compose.prod.yml exec -T postgres psql -U siber -d siber -c "${sql}"`;

const client = new Client();
client.on('ready', () => {
  client.exec(cmd, (err, stream) => {
    if (err) {
      console.error(err);
      client.end();
      process.exit(1);
    }
    stream.on('close', (code) => {
      client.end();
      process.exit(code ?? 0);
    });
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
  });
});
client.on('error', (e) => {
  console.error(e);
  process.exit(1);
});
client.connect({ host: '87.106.10.169', username: 'root', password });
