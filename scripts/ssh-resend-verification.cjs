/**
 * Resend verification email for ilkerbulut83@hotmail.com (or MAIL_TEST_TO user).
 */
const { Client } = require("C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2");

const email = process.env.MAIL_TEST_TO || "ilkerbulut83@hotmail.com";

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
  await new Promise((r, j) =>
    conn.on("ready", r).on("error", j).connect({
      host: "87.106.10.169",
      username: "root",
      password: process.env.DEPLOY_SSH_PASSWORD,
    })
  );

  const py = `
import asyncio
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.user import User
from app.services.auth_service import AuthService

async def main():
    async with async_session_factory() as db:
        r = await db.execute(select(User).where(User.email == ${JSON.stringify(email)}))
        user = r.scalar_one_or_none()
        if not user:
            print("USER_NOT_FOUND"); return
        await AuthService(db).resend_verification(user)
        await db.commit()
        print("VERIFICATION_RESENT_OK")

asyncio.run(main())
`;

  await exec(
    conn,
    `cat > /tmp/resend.py <<'EOF'
${py}
EOF
docker cp /tmp/resend.py siber-api:/app/resend.py
docker exec -w /app siber-api python3 /app/resend.py
docker logs siber-api 2>&1 | grep -E 'email\\.' | tail -5`
  );
  conn.end();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
