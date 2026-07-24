/**
 * Verify Ionos SMTP from siber-api container and resend verification.
 */
const fs = require("fs");
const os = require("os");
const path = require("path");
const { Client } = require("C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2");

const host = "87.106.10.169";
const password = process.env.DEPLOY_SSH_PASSWORD;

function exec(conn, cmd) {
  return new Promise((resolve, reject) => {
    conn.exec(cmd, (err, stream) => {
      if (err) return reject(err);
      stream.on("data", (d) => process.stdout.write(d));
      stream.stderr.on("data", (d) => process.stderr.write(d));
      stream.on("close", (code) => resolve(code));
    });
  });
}

function upload(conn, local, remote) {
  return new Promise((resolve, reject) => {
    conn.sftp((err, sftp) => {
      if (err) return reject(err);
      sftp.fastPut(local, remote, (e) => (e ? reject(e) : resolve()));
    });
  });
}

(async () => {
  const conn = new Client();
  await new Promise((r, j) => conn.on("ready", r).on("error", j).connect({ host, username: "root", password }));

  await exec(conn, "docker exec siber-api sh -c 'echo SMTP_HOST=$SMTP_HOST SMTP_USER=$SMTP_USER EMAIL_FROM=$EMAIL_FROM'");

  const py = `#!/usr/bin/env python3
import os, smtplib, sys
from email.message import EmailMessage

to = "ilkerbulut83@hotmail.com"
host = os.environ.get("SMTP_HOST")
user = os.environ.get("SMTP_USER")
pwd = os.environ.get("SMTP_PASSWORD")
frm = os.environ.get("EMAIL_FROM", user)
print("CONFIG", host, user, frm)

msg = EmailMessage()
msg["From"] = frm
msg["To"] = to
msg["Subject"] = "SIBER — E-posta doğrulama"
msg.set_content("SIBER mail test after Ionos direct configuration.")
with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", "587")), timeout=30) as s:
    s.ehlo(); s.starttls(); s.ehlo(); s.login(user, pwd)
    refused = s.send_message(msg)
    print("TEST_SEND", "OK" if not refused else refused)
    if refused:
        sys.exit(1)
`;
  const local = path.join(os.tmpdir(), "siber-ionos-verify.py");
  fs.writeFileSync(local, py, "utf8");
  await upload(conn, local, "/tmp/siber-ionos-verify.py");
  await exec(conn, "docker cp /tmp/siber-ionos-verify.py siber-api:/tmp/siber-ionos-verify.py");
  const code = await exec(conn, "docker exec siber-api python3 /tmp/siber-ionos-verify.py");

  console.log("\n=== Resend via API forgot/resend endpoint ===");
  await exec(
    conn,
    `curl -sS -X POST https://siber.cloudnira.com/api/v1/auth/forgot-password -H 'Content-Type: application/json' -d '{"email":"ilkerbulut83@hotmail.com"}' | head -c 400; echo`
  );
  await exec(conn, "docker logs siber-api 2>&1 | grep -E 'email\\.' | tail -10");

  conn.end();
  fs.unlinkSync(local);
  process.exit(code === 0 ? 0 : 1);
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
