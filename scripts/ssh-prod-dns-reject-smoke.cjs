/**
 * Live API smoke: normal user cannot start scan on unverified domain (no target traffic).
 * Requires DEPLOY_SSH_PASSWORD. Does not log tokens or passwords.
 */
const { Client } = require('C:/GOGAPP/admin.cloudnira.com/adminler/Camiiapp-admin/node_modules/ssh2');

const password = process.env.DEPLOY_SSH_PASSWORD;
if (!password) {
  console.error('DEPLOY_SSH_PASSWORD required');
  process.exit(2);
}

const cmd = `
set -e
python3 << 'PYEOF'
import json, uuid, urllib.request, urllib.error

BASE = 'http://127.0.0.1:8010'
email = f"dns-reject-{uuid.uuid4().hex[:10]}@example.com"
password_user = 'SecurePass123!Test'
hostname = f"unverified-{uuid.uuid4().hex[:8]}.example.com'

def api(method, path, body=None, token=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, json.loads(body)
        except json.JSONDecodeError:
            return e.code, {'raw': body[:200]}

st, reg = api('POST', '/api/v1/auth/register', {
    'email': email,
    'password': password_user,
    'full_name': 'DNS Reject Smoke',
})
assert st == 201, reg
token = reg['data']['tokens']['access_token']

st, org = api('POST', '/api/v1/organizations', {'name': 'DNS Reject Org'}, token=token)
assert st == 201, org
org_id = org['data']['id']

st, project = api('POST', f'/api/v1/organizations/{org_id}/projects', {
    'name': 'P', 'environment': 'staging',
}, token=token)
assert st == 201, project
project_id = project['data']['id']

st, domain = api('POST', f'/api/v1/organizations/{org_id}/projects/{project_id}/domains', {
    'hostname': hostname,
    'method': 'dns_txt',
}, token=token)
assert st == 201, domain
domain_id = domain['data']['id']
assert domain['data'].get('is_verified') is False

st, scan = api('POST', f'/api/v1/organizations/{org_id}/scans', {
    'project_id': project_id,
    'domain_id': domain_id,
    'scan_profile': 'safe',
    'target_url': f'https://{hostname}/',
    'authorization_accepted': True,
}, token=token)

code = scan.get('error', {}).get('code') if isinstance(scan, dict) else None
print('SCAN_HTTP', st)
print('ERROR_CODE', code or scan)
assert st == 400, scan
assert code == 'DOMAIN_NOT_VERIFIED', scan

# Ensure no scan row was persisted for this attempt
import subprocess
sql = (
    "SELECT count(*) FROM scan_jobs WHERE organization_id='"
    + org_id
    + "' AND target_url LIKE '%"
    + hostname
    + "%';"
)
out = subprocess.check_output([
    'docker', 'compose', '-f', '/opt/siber/docker-compose.prod.yml', 'exec', '-T', 'postgres',
    'psql', '-U', 'siber', '-d', 'siber', '-t', '-c', sql,
], cwd='/opt/siber', text=True)
count = int(out.strip() or '0')
print('SCAN_ROWS_FOR_HOST', count)
assert count == 0, 'scan job should not be queued'

print('DNS_REJECT_SMOKE_OK')
PYEOF
`;

const conn = new Client();
conn.on('ready', () => {
  conn.exec(cmd, (err, stream) => {
    if (err) {
      console.error(err.message);
      process.exit(1);
    }
    stream.on('data', (d) => process.stdout.write(d));
    stream.stderr.on('data', (d) => process.stderr.write(d));
    stream.on('close', (code) => {
      conn.end();
      process.exit(code || 0);
    });
  });
}).connect({ host: '87.106.10.169', port: 22, username: 'root', password, readyTimeout: 120000 });
