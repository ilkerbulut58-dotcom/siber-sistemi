/**
 * Verify backup restore into isolated temp database (does not touch production DB).
 */
const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');
const password = process.env.DEPLOY_SSH_PASSWORD;
const DUMP = '/opt/siber/backups/20260723T124710Z/siber-pre-deploy.dump';
const TEMP_DB = 'siber_restore_verify';

const cmd = `
set -euo pipefail
DUMP="${DUMP}"
TEMP_DB="${TEMP_DB}"
echo "=== backup file ==="
ls -la "$DUMP"
sha256sum "$DUMP"
echo "=== pg_restore list (first 10) ==="
docker exec siber-postgres pg_restore --list /tmp/siber-restore-verify.dump 2>/dev/null | head -10 || {
  docker cp "$DUMP" siber-postgres:/tmp/siber-restore-verify.dump
  docker exec siber-postgres pg_restore --list /tmp/siber-restore-verify.dump | head -10
}
echo "=== restore to temp db ==="
docker exec siber-postgres psql -U siber -d postgres -c "DROP DATABASE IF EXISTS ${TEMP_DB};"
docker exec siber-postgres psql -U siber -d postgres -c "CREATE DATABASE ${TEMP_DB};"
docker cp "$DUMP" siber-postgres:/tmp/siber-restore-verify.dump
docker exec siber-postgres pg_restore -U siber -d ${TEMP_DB} --no-owner --no-privileges /tmp/siber-restore-verify.dump
docker exec siber-postgres rm -f /tmp/siber-restore-verify.dump
echo "=== row counts ==="
docker exec siber-postgres psql -U siber -d ${TEMP_DB} -tAc "SELECT 'users', count(*) FROM users"
docker exec siber-postgres psql -U siber -d ${TEMP_DB} -tAc "SELECT 'organizations', count(*) FROM organizations"
docker exec siber-postgres psql -U siber -d ${TEMP_DB} -tAc "SELECT 'domains', count(*) FROM domains"
docker exec siber-postgres psql -U siber -d ${TEMP_DB} -tAc "SELECT 'scans', count(*) FROM scan_jobs"
docker exec siber-postgres psql -U siber -d ${TEMP_DB} -tAc "SELECT 'findings', count(*) FROM findings"
docker exec siber-postgres psql -U siber -d ${TEMP_DB} -tAc "SELECT 'audit', count(*) FROM audit_logs"
echo "=== cleanup ==="
docker exec siber-postgres psql -U siber -d postgres -c "DROP DATABASE ${TEMP_DB};"
echo BACKUP_RESTORE_VERIFY_OK
`;

async function main() {
  if (!password) { console.error('DEPLOY_SSH_PASSWORD required'); process.exit(1); }
  const conn = new Client();
  await new Promise((resolve, reject) => {
    conn.on('ready', () => {
      conn.exec(cmd, (err, stream) => {
        if (err) return reject(err);
        stream.on('data', (d) => process.stdout.write(d));
        stream.stderr.on('data', (d) => process.stderr.write(d));
        stream.on('close', (code) => { conn.end(); code === 0 ? resolve() : reject(new Error(`exit ${code}`)); });
      });
    });
    conn.on('error', reject);
    conn.connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 300000 });
  });
}

main().catch((e) => { console.error(e.message); process.exit(1); });
