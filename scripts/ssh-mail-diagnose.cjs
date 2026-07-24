/**
 * Diagnose outbound mail on production (no secrets printed).
 * Requires DEPLOY_SSH_PASSWORD
 */
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

(async () => {
  if (!password) {
    console.error("DEPLOY_SSH_PASSWORD required");
    process.exit(1);
  }
  const conn = new Client();
  await new Promise((r, j) => conn.on("ready", r).on("error", j).connect({ host, username: "root", password }));

  const cmds = [
    "echo '=== RESOLVER ==='",
    "cat /etc/resolv.conf | grep -v '^#' | grep . || true",
    "echo '=== MX hotmail.com ==='",
    "dig +short MX hotmail.com @8.8.8.8 2>/dev/null || nslookup -type=mx hotmail.com 8.8.8.8 2>&1 | tail -5",
    "echo '=== MX from local resolver ==='",
    "dig +short MX hotmail.com 2>/dev/null || nslookup -type=mx hotmail.com 2>&1 | tail -5",
    "echo '=== POSTFIX status ==='",
    "postfix status 2>&1 || systemctl is-active postfix 2>&1",
    "echo '=== POSTFIX relay / smarthost ==='",
    "postconf relayhost smtpd_relay_restrictions smtpd_recipient_restrictions 2>/dev/null | head -20",
    "echo '=== Recent mail log (grep) ==='",
    "grep -E 'postfix|smtp|status=' /var/log/maillog 2>/dev/null | tail -30 || grep -E 'postfix|smtp|status=' /var/log/mail.log 2>/dev/null | tail -30 || journalctl -u postfix --no-pager -n 30 2>/dev/null",
    "echo '=== Docker API SMTP env (redacted) ==='",
    "docker exec siber-api sh -c 'echo SMTP_ENABLED=$SMTP_ENABLED SMTP_HOST=$SMTP_HOST SMTP_PORT=$SMTP_PORT SMTP_USER=$SMTP_USER EMAIL_FROM=$EMAIL_FROM'",
    "echo '=== Recent API email logs ==='",
    "docker logs siber-api 2>&1 | grep -E 'email\\.' | tail -15",
    "echo '=== Docker -> host.docker.internal:587 ==='",
    "docker exec siber-api sh -c 'nc -zv host.docker.internal 587 2>&1 || timeout 3 bash -c \"echo > /dev/tcp/host.docker.internal/587\" 2>&1 || echo PORT_CHECK_FAILED'",
  ];

  for (const cmd of cmds) {
    await exec(conn, cmd);
  }
  conn.end();
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
