/**
 * Regenerate scan PDF on production from existing DB evidence (no rescan).
 * Usage: DEPLOY_SSH_PASSWORD=... node scripts/ssh-export-scan-report-pdf.cjs <scan-uuid> [tr|de]
 */
const fs = require('fs');
const path = require('path');
const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
const scanId = process.argv[2] || '';
const locale = process.argv[3] || 'tr';
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

if (!password || !scanId) {
  console.error('Usage: DEPLOY_SSH_PASSWORD=... node ssh-export-scan-report-pdf.cjs <scan-id> [tr|de]');
  process.exit(1);
}
if (!UUID_RE.test(scanId)) {
  console.error('invalid scan uuid');
  process.exit(1);
}
if (locale !== 'tr' && locale !== 'de') {
  console.error('locale must be tr or de');
  process.exit(1);
}

const outDir = path.join(__dirname, '..', 'docs', 'reports', 'samples');
const outName = `scan-${scanId.slice(0, 8)}-report-${locale}.pdf`;
const stamp = `${Date.now()}-${process.pid}`;
const fileName = `siber-export-${stamp}.pdf`;
const containerPath = `/tmp/${fileName}`;
const hostPath = `/var/tmp/${fileName}`;

const py = `
import asyncio, os, uuid
from pathlib import Path
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.scan import ScanJob
from app.services.report_service import ReportService

scan_id = uuid.UUID(os.environ["SIBER_EXPORT_SCAN_ID"])
locale = os.environ["SIBER_EXPORT_LOCALE"]
out = Path(os.environ["SIBER_EXPORT_OUT"])
if out.parent != Path("/tmp") or not out.name.startswith("siber-export-") or out.suffix != ".pdf":
    raise SystemExit("BAD_PATH")
if locale not in {"tr", "de"}:
    raise SystemExit("BAD_LOCALE")

async def main():
    async with async_session_factory() as db:
        scan = (await db.execute(select(ScanJob).where(ScanJob.id == scan_id))).scalar_one_or_none()
        if not scan:
            raise SystemExit("SCAN_NOT_FOUND")
        content, _, _ = await ReportService(db).build(scan.organization_id, scan_id, "pdf", locale)
        out.write_bytes(content)
        out.chmod(0o600)
        print("WROTE", out.name, len(content), flush=True)

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
      sftp.fastGet(remote, local, (e) => {
        sftp.end();
        if (e) reject(e);
        else resolve();
      });
    });
  });
}

function isPdfFile(filePath) {
  if (!fs.existsSync(filePath)) return false;
  const st = fs.statSync(filePath);
  if (st.size < 100) return false;
  const fd = fs.openSync(filePath, 'r');
  try {
    const buf = Buffer.alloc(5);
    fs.readSync(fd, buf, 0, 5, 0);
    return buf.toString('utf8') === '%PDF-';
  } finally {
    fs.closeSync(fd);
  }
}

(async () => {
  const conn = new Client();
  let containerWrote = false;
  let hostCopied = false;
  try {
    await new Promise((r, j) => conn.on('ready', r).on('error', j).connect({
      host: '87.106.10.169', username: 'root', password, readyTimeout: 120000,
    }));
    console.log('stage: generate-in-container');
    const run = [
      'docker exec',
      `-e SIBER_EXPORT_SCAN_ID=${scanId}`,
      `-e SIBER_EXPORT_LOCALE=${locale}`,
      `-e SIBER_EXPORT_OUT=${containerPath}`,
      '-i siber-api python3 <<\'PY\'',
      py.trim(),
      'PY',
    ].join(' ');
    const genOut = await exec(conn, run);
    console.log(genOut.trim());
    if (!genOut.includes('WROTE')) {
      throw new Error('container did not write PDF');
    }
    containerWrote = true;
    console.log('stage: docker-cp-to-host');
    await exec(conn, `docker cp siber-api:${containerPath} ${hostPath} && chmod 600 ${hostPath}`);
    hostCopied = true;
    console.log('stage: sftp-download');
    fs.mkdirSync(outDir, { recursive: true });
    const localPath = path.join(outDir, outName);
    await sftpGet(conn, hostPath, localPath);
    if (!isPdfFile(localPath)) {
      throw new Error('downloaded file is missing or not a PDF');
    }
    console.log('Saved', localPath, 'bytes', fs.statSync(localPath).size);
  } catch (e) {
    console.error(e instanceof Error ? e.message : e);
    process.exitCode = 1;
  } finally {
    try {
      if (containerWrote) {
        console.log('stage: cleanup-container');
        await exec(conn, `docker exec siber-api rm -f ${containerPath}`);
      }
    } catch (cleanupErr) {
      console.error('cleanup-container failed');
    }
    try {
      if (hostCopied) {
        console.log('stage: cleanup-host');
        await exec(conn, `rm -f ${hostPath}`);
      }
    } catch (cleanupErr) {
      console.error('cleanup-host failed');
    }
    conn.end();
  }
})();
