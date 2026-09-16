/**
 * Live API smoke: normal user cannot start scan on unverified domain.
 *
 * Second control if authorization incorrectly allows the request:
 * hostname is RFC 5737 TEST-NET-1 (192.0.2.1). Production url_guard
 * treats it as a blocked IP, so validate_scan_target_url fails before
 * ScanJob persist / dispatch_scan_job. No HTTP to a live site.
 *
 * Does not change production registration policy. Does not log tokens.
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
import json, uuid, urllib.request, urllib.error, subprocess

BASE = 'http://127.0.0.1:8010'
email = f"dns-reject-{uuid.uuid4().hex[:10]}@example.com"
password_user = 'SecurePass123!Test'
# RFC 5737 documentation address — url_guard blocks even if DNS auth fails open.
hostname = '192.0.2.1'

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
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {'raw': raw[:200]}

def docker_out(args):
    return subprocess.check_output(args, cwd='/opt/siber', text=True)

def redis_llen():
    try:
        out = docker_out([
            'docker', 'compose', '-f', '/opt/siber/docker-compose.prod.yml',
            'exec', '-T', 'redis', 'redis-cli', 'LLEN', 'scans',
        ])
        return int((out or '0').strip() or '0')
    except Exception as exc:
        print('REDIS_LLEN_ERROR', type(exc).__name__)
        return None

llen_before = redis_llen()
print('REDIS_LLEN_BEFORE', llen_before)

st, reg = api('POST', '/api/v1/auth/register', {
    'email': email,
    'password': password_user,
    'full_name': 'DNS Reject Smoke',
})
assert st == 201, reg
print('SMOKE_USER', email)
token = reg['data']['tokens']['access_token']

st, org = api('POST', '/api/v1/organizations', {'name': 'DNS Reject Org'}, token=token)
assert st == 201, org
org_id = org['data']['id']
print('SMOKE_ORG', org_id)

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
print('DOMAIN_VERIFIED', domain['data'].get('is_verified'))

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
assert st != 201, 'scan must not be created'
assert st == 400, scan
assert code == 'DOMAIN_NOT_VERIFIED', scan

sql_jobs = (
    "SELECT count(*) FROM scan_jobs WHERE organization_id='"
    + org_id
    + "';"
)
sql_celery = (
    "SELECT count(*) FROM scan_jobs WHERE organization_id='"
    + org_id
    + "' AND celery_task_id IS NOT NULL;"
)
jobs = int(docker_out([
    'docker', 'compose', '-f', '/opt/siber/docker-compose.prod.yml', 'exec', '-T', 'postgres',
    'psql', '-U', 'siber', '-d', 'siber', '-t', '-A', '-c', sql_jobs,
]).strip() or '0')
celery_rows = int(docker_out([
    'docker', 'compose', '-f', '/opt/siber/docker-compose.prod.yml', 'exec', '-T', 'postgres',
    'psql', '-U', 'siber', '-d', 'siber', '-t', '-A', '-c', sql_celery,
]).strip() or '0')
print('SCAN_ROWS_FOR_ORG', jobs)
print('SCAN_CELERY_TASK_ROWS', celery_rows)
assert jobs == 0, 'scan job should not be persisted'
assert celery_rows == 0, 'celery task id should not be stored'

llen_after = redis_llen()
print('REDIS_LLEN_AFTER', llen_after)
if llen_before is not None and llen_after is not None:
    assert llen_after == llen_before, 'celery scans queue length changed'
else:
    raise SystemExit('could not read redis scans queue length')

print('DNS_REJECT_SMOKE_OK')
print('SECOND_CONTROL url_guard blocked-IP 192.0.2.1 if auth had allowed')
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
