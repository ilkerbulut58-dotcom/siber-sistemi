/**
 * Point SIBER at Ionos SMTP (authorized sender) and resend verification email.
 */
const { Client } = require("C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2");

const host = "87.106.10.169";
const password = process.env.DEPLOY_SSH_PASSWORD;
const testTo = process.env.MAIL_TEST_TO || "ilkerbulut83@hotmail.com";

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

(async () => {
  const conn = new Client();
  await new Promise((r, j) => conn.on("ready", r).on("error", j).connect({ host, username: "root", password }));

  console.log("=== Configure SIBER for direct Ionos SMTP ===");
  const patchResult = await exec(
    conn,
    `python3 <<'PY'
import re
from pathlib import Path

env_path = Path("/opt/siber/.env")
text = env_path.read_text() if env_path.exists() else ""

# Read Ionos relay credentials already on server
user = pwd = None
for line in Path("/etc/postfix/sasl_passwd").read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    _, cred = line.split(None, 1)
    user, pwd = cred.split(":", 1)
    break
if not user or not pwd:
    raise SystemExit("IONOS_CREDS_NOT_FOUND")

updates = {
    "SMTP_ENABLED": "true",
    "SMTP_HOST": "smtp.ionos.de",
    "SMTP_PORT": "587",
    "SMTP_USER": user,
    "SMTP_PASSWORD": pwd,
    "SMTP_USE_TLS": "true",
    "EMAIL_FROM": f'"SIBER <{user}>"',
    "FRONTEND_PUBLIC_URL": "https://siber.cloudnira.com",
}

for key, val in updates.items():
    text = re.sub(rf"^{key}=.*\\n?", "", text, flags=re.M)
text = text.rstrip() + "\\n\\n# --- SIBER SMTP (Ionos direct) ---\\n"
for key, val in updates.items():
    text += f"{key}={val}\\n"
env_path.write_text(text)
print("ENV_PATCHED", user)
PY`
  );

  console.log("\n=== Restart API/worker ===");
  await exec(conn, "cd /opt/siber && docker compose -f docker-compose.prod.yml up -d api worker");

  console.log("\n=== Test send to hotmail from container ===");
  await exec(conn, "sleep 5");
  const sendCode = await exec(
    conn,
    `docker exec siber-api python3 <<'PY'
import os, smtplib, sys
from email.message import EmailMessage
to = ${JSON.stringify(testTo)}
user = os.environ["SMTP_USER"]
pwd = os.environ["SMTP_PASSWORD"]
frm = os.environ.get("EMAIL_FROM", user)
msg = EmailMessage()
msg["From"] = frm
msg["To"] = to
msg["Subject"] = "SIBER — E-posta doğrulama testi"
msg.set_content("SIBER mail Ionos direct test. Bu mesaji aldiysaniz sistem calisiyor.")
try:
    with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")), timeout=30) as s:
        s.ehlo(); s.starttls(); s.ehlo(); s.login(user, pwd)
        refused = s.send_message(msg)
        if refused:
            print("REFUSED", refused); sys.exit(1)
    print("IONOS_SEND_OK")
except Exception as e:
    print("IONOS_SEND_FAIL", type(e).__name__, e); sys.exit(1)
PY`
  );

  if (sendCode !== 0) {
    conn.end();
    process.exit(1);
  }

  console.log("\n=== Resend verification for ilkerbulut83@hotmail.com ===");
  await exec(
    conn,
    `docker exec siber-api python3 <<'PY'
import asyncio
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.user import User
from app.services.auth_service import AuthService

async def main():
    async with async_session_factory() as db:
        r = await db.execute(select(User).where(User.email == "ilkerbulut83@hotmail.com"))
        user = r.scalar_one_or_none()
        if not user:
            print("USER_NOT_FOUND"); return
        svc = AuthService(db)
        await svc.resend_verification(user)
        await db.commit()
        print("VERIFICATION_RESENT_OK")

asyncio.run(main())
PY`
  );

  await exec(conn, "docker logs siber-api 2>&1 | grep -E 'email\\.' | tail -8");
  conn.end();
  console.log("\nIONOS_MAIL_CONFIGURED");
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
