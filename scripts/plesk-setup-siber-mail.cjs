/**
 * Create noreply@cloudnira.com on Plesk and configure /opt/siber/.env SMTP vars.
 *
 * Requires: DEPLOY_SSH_PASSWORD
 * Does NOT print mailbox password to stdout (written to server .env only).
 */
const crypto = require('crypto');
const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const host = '87.106.10.169';
const password = process.env.DEPLOY_SSH_PASSWORD;
const remoteRoot = '/opt/siber';
const mailUser = 'noreply@cloudnira.com';

function exec(conn, cmd) {
  return new Promise((resolve, reject) => {
    conn.exec(cmd, (err, stream) => {
      if (err) return reject(err);
      let out = '';
      stream.on('data', (d) => {
        out += d.toString();
        process.stdout.write(d);
      });
      stream.stderr.on('data', (d) => {
        out += d.toString();
        process.stderr.write(d);
      });
      stream.on('close', (code) => resolve({ code, out }));
    });
  });
}

function shellQuote(value) {
  return `'${String(value).replace(/'/g, `'\\''`)}'`;
}

async function main() {
  if (!password) {
    console.error('DEPLOY_SSH_PASSWORD required');
    process.exit(1);
  }

  const mailboxPassword = crypto.randomBytes(24).toString('base64url');
  const conn = new Client();
  await new Promise((resolve, reject) => {
    conn.on('ready', resolve).on('error', reject).connect({ host, username: 'root', password });
  });

  console.log('=== Ensure mailbox exists ===');
  const info = await exec(conn, `plesk bin mail --info ${mailUser} 2>&1 || true`);
  if (/Mailname:/.test(info.out)) {
    console.log('Updating existing mailbox password...');
    await exec(
      conn,
      `plesk bin mail --update ${mailUser} -passwd ${shellQuote(mailboxPassword)} -passwd_type plain`
    );
  } else {
    console.log('Creating mailbox...');
    await exec(
      conn,
      `plesk bin mail --create ${mailUser} -mailbox true -passwd ${shellQuote(mailboxPassword)} -passwd_type plain`
    );
  }

  console.log('\n=== Update /opt/siber/.env ===');
  const remoteScript = `set -euo pipefail
ENV_FILE=${remoteRoot}/.env
[ -f "$ENV_FILE" ] || cp ${remoteRoot}/deploy/production.env.example "$ENV_FILE"
for KEY in SMTP_ENABLED SMTP_HOST SMTP_PORT SMTP_USER SMTP_PASSWORD SMTP_USE_TLS EMAIL_FROM FRONTEND_PUBLIC_URL; do
  sed -i "/^\${KEY}=/d" "$ENV_FILE"
done
sed -i '/# --- SIBER SMTP/,/^FRONTEND_PUBLIC_URL=/d' "$ENV_FILE" 2>/dev/null || true
cat >> "$ENV_FILE" <<'EOF'

# --- SIBER SMTP (Plesk Postfix) ---
SMTP_ENABLED=true
SMTP_HOST=host.docker.internal
SMTP_PORT=587
SMTP_USER=${mailUser}
SMTP_PASSWORD=${mailboxPassword}
SMTP_USE_TLS=true
EMAIL_FROM=SIBER <${mailUser}>
FRONTEND_PUBLIC_URL=https://siber.cloudnira.com
EOF
chmod 600 "$ENV_FILE"
echo "ENV updated"
`;
  await exec(conn, remoteScript);

  console.log('\n=== SMTP test from host (127.0.0.1:587) ===');
  const testPy =
    'import smtplib\n' +
    'from email.message import EmailMessage\n' +
    `user=${JSON.stringify(mailUser)}\n` +
    `pwd=${JSON.stringify(mailboxPassword)}\n` +
    'msg=EmailMessage()\n' +
    'msg["From"]=f"SIBER <{user}>"\n' +
    'msg["To"]=user\n' +
    'msg["Subject"]="SIBER SMTP self-test"\n' +
    'msg.set_content("SMTP configuration OK.")\n' +
    'with smtplib.SMTP("127.0.0.1", 587, timeout=20) as s:\n' +
    '    s.starttls()\n' +
    '    s.login(user, pwd)\n' +
    '    s.send_message(msg)\n' +
    'print("HOST_SMTP_TEST_OK")\n';
  const testResult = await exec(conn, `python3 -c ${shellQuote(testPy)}`);
  if (!/HOST_SMTP_TEST_OK/.test(testResult.out)) {
    console.error('Host SMTP test failed');
    conn.end();
    process.exit(1);
  }

  console.log('\n=== Restart SIBER API/worker ===');
  await exec(conn, `cd ${remoteRoot} && docker compose -f docker-compose.prod.yml up -d api worker`);

  console.log('\nPLESK_SIBER_MAIL_SETUP_OK');
  console.log(`Mailbox: ${mailUser}`);
  console.log('Password stored in /opt/siber/.env only.');
  console.log('\nDNS (Ionos — cloudnira.com): update SPF TXT, e.g.:');
  console.log('  v=spf1 include:_spf.perfora.net include:_spf.kundenserver.de ip4:87.106.10.169 ~all');
  conn.end();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
