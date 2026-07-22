const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const host = '87.106.10.169';
const username = 'root';
const password = process.env.DEPLOY_SSH_PASSWORD;
const baseUrl = 'https://siber.cloudnira.com';

function exec(conn, cmd) {
  return new Promise((resolve, reject) => {
    conn.exec(cmd, (err, stream) => {
      if (err) return reject(err);
      let out = '';
      stream.on('data', (d) => { out += d.toString(); process.stdout.write(d); });
      stream.stderr.on('data', (d) => { out += d.toString(); process.stderr.write(d); });
      stream.on('close', (code) => (code === 0 ? resolve(out) : reject(new Error(`exit ${code}`))));
    });
  });
}

async function apiTest(label, fn) {
  try {
    const result = await fn();
    console.log(`\n[OK] ${label}`);
    return result;
  } catch (e) {
    console.log(`\n[FAIL] ${label}: ${e.message}`);
    throw e;
  }
}

async function main() {
  if (!password) {
    console.error('DEPLOY_SSH_PASSWORD required');
    process.exit(1);
  }

  console.log('=== SSH REMOTE CHECKS ===\n');
  const conn = new Client();
  await new Promise((resolve, reject) => {
    conn.on('ready', async () => {
      try {
        await exec(conn, `
echo "--- Docker status ---"
cd /opt/siber && docker compose -f docker-compose.prod.yml ps

echo ""
echo "--- SKIP_DOMAIN_VERIFICATION in .env ---"
grep SKIP_DOMAIN_VERIFICATION /opt/siber/.env || true

echo ""
echo "--- Health (localhost) ---"
curl -s http://127.0.0.1:8010/api/v1/health

echo ""
echo ""
echo "--- Health (public) ---"
curl -s ${baseUrl}/api/v1/health -k

echo ""
echo ""
echo "--- Login test (localhost) ---"
curl -s -X POST http://127.0.0.1:8010/api/v1/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email":"admin","password":"admin"}'
echo ""
`);
        conn.end();
        resolve();
      } catch (e) {
        conn.end();
        reject(e);
      }
    });
    conn.on('error', reject);
    conn.connect({ host, port: 22, username, password, readyTimeout: 30000 });
  });

  console.log('\n=== PUBLIC API FLOW TEST ===\n');

  const health = await fetch(`${baseUrl}/api/v1/health`).then((r) => r.json());
  await apiTest('Health endpoint', () => {
    if (!health.success) throw new Error(JSON.stringify(health));
    console.log(JSON.stringify(health.data, null, 2));
    return health.data;
  });

  const loginRes = await fetch(`${baseUrl}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: 'admin', password: 'admin' }),
  });
  const loginBody = await loginRes.json();
  const loginData = await apiTest('Login admin/admin', () => {
    if (!loginRes.ok || !loginBody.success) throw new Error(loginBody.error?.message || 'login failed');
    console.log(`User: ${loginBody.data.user.email}, token length: ${loginBody.data.tokens.access_token.length}`);
    return loginBody.data;
  });

  const token = loginData.tokens.access_token;
  const auth = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const orgsRes = await fetch(`${baseUrl}/api/v1/organizations`, { headers: auth });
  const orgsBody = await orgsRes.json();
  const orgs = await apiTest('List organizations', () => {
    if (!orgsBody.success) throw new Error(orgsBody.error?.message);
    console.log(`Organizations: ${orgsBody.data.length}`);
    return orgsBody.data;
  });

  let orgId = orgs[0]?.id;
  if (!orgId) {
    const createOrg = await fetch(`${baseUrl}/api/v1/organizations`, {
      method: 'POST',
      headers: auth,
      body: JSON.stringify({ name: 'Test Org', slug: `test-${Date.now()}` }),
    }).then((r) => r.json());
    orgId = createOrg.data?.id;
    console.log(`Created org: ${orgId}`);
  }

  const projectsRes = await fetch(`${baseUrl}/api/v1/organizations/${orgId}/projects`, { headers: auth });
  const projectsBody = await projectsRes.json();
  let projectId = projectsBody.data?.[0]?.id;
  if (!projectId) {
    const createProj = await fetch(`${baseUrl}/api/v1/organizations/${orgId}/projects`, {
      method: 'POST',
      headers: auth,
      body: JSON.stringify({ name: 'Test Project', slug: `proj-${Date.now()}` }),
    }).then((r) => r.json());
    projectId = createProj.data?.id;
    console.log(`Created project: ${projectId}`);
  }

  const testHost = `test-${Date.now()}.example.com`;
  const addDomain = await fetch(
    `${baseUrl}/api/v1/organizations/${orgId}/projects/${projectId}/domains`,
    {
      method: 'POST',
      headers: auth,
      body: JSON.stringify({ hostname: testHost, verification_method: 'dns_txt' }),
    }
  ).then((r) => r.json());

  await apiTest('Add domain', () => {
    if (!addDomain.success) throw new Error(addDomain.error?.message);
    console.log(`Domain: ${addDomain.data.domain.hostname}, verified: ${addDomain.data.domain.is_verified}`);
    return addDomain.data;
  });

  const domainId = addDomain.data.domain.id;

  const instructions = await fetch(
    `${baseUrl}/api/v1/organizations/${orgId}/projects/${projectId}/domains/${domainId}/verification-instructions`,
    { headers: auth }
  ).then((r) => r.json());

  await apiTest('Verification instructions', () => {
    if (!instructions.success) throw new Error(instructions.error?.message);
    console.log(`Method: ${instructions.data.method}, token: ${instructions.data.token.slice(0, 12)}...`);
    return instructions.data;
  });

  const verify = await fetch(
    `${baseUrl}/api/v1/organizations/${orgId}/projects/${projectId}/domains/${domainId}/verify`,
    { method: 'POST', headers: auth }
  ).then((r) => r.json());

  await apiTest('Verify domain (expect fail for fake domain)', () => {
    if (!verify.success) throw new Error(verify.error?.message);
    console.log(`Verified: ${verify.data.verified}, message: ${verify.data.message}`);
    return verify.data;
  });

  // Test expired token scenario - use garbage token
  const badToken = await fetch(`${baseUrl}/api/v1/organizations`, {
    headers: { Authorization: 'Bearer invalid.token.here', 'Content-Type': 'application/json' },
  }).then((r) => r.json());

  await apiTest('Invalid token returns expected error', () => {
    const msg = badToken.error?.message || '';
    if (!msg.includes('Invalid or expired token')) throw new Error(`Unexpected: ${msg}`);
    console.log(`Error message: ${msg}`);
    return msg;
  });

  console.log('\n=== ALL TESTS COMPLETE ===');
}

main().catch((e) => {
  console.error('\nTest run failed:', e.message);
  process.exit(1);
});
