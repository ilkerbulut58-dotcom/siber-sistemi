/**
 * Regenerate scan PDF on production from existing DB evidence (no rescan).
 * Usage: DEPLOY_SSH_PASSWORD=... node scripts/ssh-export-scan-report-pdf.cjs <scan-uuid> [tr|de]
 */
const fs = require('fs');
const path = require('path');
const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const scanId = process.argv[2];
const locale = process.argv[3] || 'tr';
if (!password || !scanId) {
  console.error('Usage: DEPLOY_SSH_PASSWORD=... node ssh-export-scan-report-pdf.cjs <scan-id> [tr|de]');
  process.exit(1);
}

const outDir = path.join(__dirname, '..', 'docs', 'reports', 'samples');
const outName = `scan-${scanId.slice(0, 8)}-report-${locale}.pdf`;
const remotePath = `/tmp/${outName}`;

const py = `
import asyncio, uuid
from pathlib import Path
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.scan import ScanJob
from app.services.report_service import ReportService

SCAN_ID = uuid.UUID("${scanId}")
LOCALE = ${JSON.stringify(locale)}
OUT = Path(${JSON.stringify(remotePath)})

async def main():
    async with async_session_factory() as db:
        scan = (await db.execute(select(ScanJob).where(ScanJob.id == SCAN_ID))).scalar_one_or_none()
        if not scan:
            raise SystemExit("SCAN_NOT_FOUND")
        content, _, _ = await ReportService(db).build(scan.organization_id, SCAN_ID, "pdf", LOCALE)
        OUT.write_bytes(content)
        print("WROTE", OUT, len(content))

asyncio.run(main())
`;

function exec(conn, cmd) {
  return new Promise((resolve, reject) => {
    conn.exec(cmd, (err, stream) => {
      if (err) return reject(err);
      let out = '';
      stream.on('data', (d) => (out += d.toString()));
      stream.stderr.on('data', (d) => (out += d.toString()));
      stream.on('close', (code) => (code === 0 ? resolve(out) : reject(new Error(out || `exit ${code}`))));
    });
  });
}

function sftpGet(conn, remote, local) {
  return new Promise((resolve, reject) => {
    conn.sftp((err, sftp) => {
      if (err) return reject(err);
      sftp.fastGet(remote, local, (e) => (e ? reject(e) : resolve()));
    });
  });
}

(async () => {
  const conn = new Client();
  await new Promise((r, j) => conn.on('ready', r).on('error', j).connect({ host: '87.106.10.169', username: 'root', password }));
  const run = `docker exec -i siber-api python3 <<'PY'\n${py}\nPY`;
  console.log(await exec(conn, run));
  fs.mkdirSync(outDir, { recursive: true });
  const localPath = path.join(outDir, outName);
  await sftpGet(conn, remotePath, localPath);
  console.log('Saved', localPath);
  conn.end();
})().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
