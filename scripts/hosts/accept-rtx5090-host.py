#!/usr/bin/env python3
"""WSL-side bounded acceptance window with an independent restoration watchdog.

All durable state is private to --workspace. Restoration is lock-protected and
safe to invoke independently of route success. --dry-run has no effects.
"""
import argparse
import base64
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--action', required=True, choices=('preflight', 'begin', 'restore', 'watchdog', 'host-route', 'setup', 'identity', 'linux-live', 'linux-outage', 'beta-start', 'beta-stop'))
    for name in ('workspace', 'release', 'candidate', 'windows-workspace', 'production-image'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--production', default='ninfer-5090-v070p')
    p.add_argument('--window-dir', default='/home/sunil/services/engine-window')
    p.add_argument('--restore-after-seconds', type=int, default=3000, help='Independent watchdog delay; reserve restoration time inside the total envelope')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    if a.dry_run:
        print(json.dumps({'status': 'dry-run', 'action': a.action, 'effects': 'none', 'restoration': ['remove beta', 'window.sh restore', 'WSL and Windows health', 'original key and checkout', 'own hold only']}))
        return
    root = Path(a.workspace).expanduser().resolve()
    home = Path.home()
    clone = root / 'candidate'
    checkout = home / 'omp-ninfer'
    key = home / '.config/omp-ninfer/api-key'
    logs = home / '.local/state/omp-ninfer'
    checkpoints = home / '.local/share/omp-ninfer/checkpoints'
    os.environ['PATH'] = '/usr/bin:/bin:/usr/local/bin:/usr/lib/wsl/lib:' + os.environ.get('PATH', '')
    def save(name, value):
        (root / name).write_text(json.dumps(value, indent=2) + '\n')
    def run(argv, timeout=60, env=None):
        r = subprocess.run([str(s) for s in argv], capture_output=True, text=True, timeout=timeout, env=env)
        if r.returncode:
            raise RuntimeError('command failed: ' + str(argv[0]) + ' (exit ' + str(r.returncode) + '): ' + r.stderr[-1200:])
        return r.stdout.strip()
    def logged(name, argv, timeout, env=None):
        with (root / name).open('w') as log:
            r = subprocess.run([str(s) for s in argv], stdout=log, stderr=subprocess.STDOUT, timeout=timeout, env=env)
        assert r.returncode == 0, name + ' failed: exit ' + str(r.returncode)
    def inspect(name):
        return json.loads(run(['docker', 'inspect', '--format', '{{json .}}', name]))
    def health(port):
        with urllib.request.urlopen('http://127.0.0.1:' + str(port) + '/health', timeout=10) as r:
            assert r.status == 200
            return json.load(r)
    def ps(action):
        quote = lambda s: "'" + str(s).replace("'", "''") + "'"
        text = "& ([scriptblock]::Create([IO.File]::ReadAllText(" + quote(a.windows_workspace + '\\accept-windows-client.ps1') + "))) -Action " + action + " -Workspace " + quote(a.windows_workspace) + " -Release " + quote(a.release) + " -Candidate " + quote(a.candidate)
        return run(['/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-EncodedCommand', base64.b64encode(text.encode('utf-16le')).decode()], 90)
    def baseline():
        d = inspect(a.production)
        assert d['Config']['Image'] == a.production_image and d['State']['Running'] and d['HostConfig']['RestartPolicy']['Name'] == 'unless-stopped', 'production baseline changed'
        assert health(18088)['status'] == 'ok'
        assert run(['git', '-C', checkout, 'status', '--porcelain']) == '', 'original checkout dirty'
        assert not subprocess.run(['docker', 'inspect', 'omp-ninfer-beta'], capture_output=True).returncode == 0, 'beta container already exists'
        return {'started_utc': now(), 'checkout': run(['git', '-C', checkout, 'rev-parse', 'HEAD']), 'branch': run(['git', '-C', checkout, 'rev-parse', '--abbrev-ref', 'HEAD']),
                'production_image': d['Config']['Image'], 'production_image_id': d['Image'], 'restart': d['HostConfig']['RestartPolicy']['Name'],
                'mounts': d['Mounts'], 'health': health(18088), 'key_sha256': digest(key),
                'directories': {str(v): {'mode': v.stat().st_mode & 0o777, 'atime_ns': v.stat().st_atime_ns, 'mtime_ns': v.stat().st_mtime_ns} for v in (key.parent, home / '.local/share/omp-ninfer', logs, checkpoints)}}
    def restore():
        with (root / 'restore.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if (root / 'restoration.json').exists():
                return
            if not (root / 'baseline.json').exists():
                baseline()
                ps('Release')
                save('restoration.json', {'completed_utc': now(), 'production_untouched': True, 'own_hold_released': True})
                return
            b = json.loads((root / 'baseline.json').read_text())
            result = {'started_utc': now()}
            subprocess.run(['docker', 'rm', '-f', 'omp-ninfer-beta'], capture_output=True, timeout=120)
            d = inspect(a.production)
            already_healthy = False
            if d['State']['Running'] and d['Config']['Image'] == b['production_image'] and d['HostConfig']['RestartPolicy']['Name'] == 'unless-stopped':
                try:
                    already_healthy = health(18088).get('status') == 'ok'
                except Exception:
                    pass
            if not already_healthy:
                logged('production-restore.log', ['bash', Path(a.window_dir) / 'window.sh', 'restore'], 480)
            for _ in range(60):
                try:
                    if health(18088).get('status') == 'ok':
                        break
                except Exception:
                    pass
                time.sleep(2)
            d = inspect(a.production)
            result.update({'health': health(18088), 'image': d['Config']['Image'], 'same_image': d['Config']['Image'] == b['production_image'] and d['Image'] == b['production_image_id'],
                           'restart': d['HostConfig']['RestartPolicy']['Name'], 'running': d['State']['Running'], 'mounts': d['Mounts'], 'checkpoint_mount_retained': sorted(d['Mounts'], key=lambda v: v['Destination']) == sorted(b['mounts'], key=lambda v: v['Destination'])})
            assert result['same_image'] and result['running'] and result['restart'] == 'unless-stopped' and result['health']['status'] == 'ok' and result['checkpoint_mount_retained'], 'production restoration proof failed'
            # Rename original directories back intact. New route state remains private.
            for label, path in (('logs', logs), ('checkpoints', checkpoints)):
                original = root / ('original-' + label)
                if original.exists():
                    if path.exists():
                        path.rename(root / ('window-' + label))
                    original.rename(path)
            if (root / 'original-api-key').exists():
                if key.exists():
                    key.unlink()
                (root / 'original-api-key').rename(key)
            result['documented_key_restored'] = digest(key) == b['key_sha256']
            target = b['checkout'] if b['branch'] == 'HEAD' else b['branch']
            run(['git', '-C', checkout, 'checkout', '-q', target])
            result['checkout'] = run(['git', '-C', checkout, 'rev-parse', 'HEAD'])
            result['branch'] = run(['git', '-C', checkout, 'rev-parse', '--abbrev-ref', 'HEAD'])
            result['checkout_restored'] = result['checkout'] == b['checkout'] and result['branch'] == b['branch'] and run(['git', '-C', checkout, 'status', '--porcelain']) == ''
            for path, metadata in b['directories'].items():
                os.chmod(path, metadata['mode'])
                os.utime(path, ns=(metadata['atime_ns'], metadata['mtime_ns']))
            assert result['documented_key_restored'] and result['checkout_restored']
            result['beta_absent'] = subprocess.run(['docker', 'inspect', 'omp-ninfer-beta'], capture_output=True).returncode != 0
            assert result['beta_absent']
            result['windows_release'] = ps('Release')
            result['completed_utc'] = now()
            result['window_seconds'] = round(time.time() - b['start_epoch'], 3)
            save('restoration.json', result)
    env = dict(os.environ, DOCKER_CONFIG=str(root / 'anonymous-docker'))
    if a.action == 'preflight':
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(root, 0o700)
        if not clone.exists():
            run(['git', 'clone', '-q', 'https://github.com/alphastorm/omp-ninfer.git', clone], 180)
            run(['git', '-C', clone, 'checkout', '-q', a.candidate])
        assert run(['git', '-C', clone, 'rev-parse', 'HEAD']) == a.candidate and not run(['git', '-C', clone, 'status', '--porcelain'])
        logged('candidate-verification.log', [sys.executable, clone / 'scripts/verify_release.py', '--release', a.release, '--require-installable'], 120)
        bundle = root / 'host-bundle'
        if not bundle.exists():
            run([sys.executable, clone / 'scripts/documented_route.py', 'bundle', '--lane', 'rtx5090-container-host', '--output', bundle])
        comp = json.loads((clone / 'compatibility.json').read_text())
        profile = next(v for v in comp['profiles'] if v['id'] == 'linux-docker-local')
        runtime, dist = profile['runtime'], profile['client_distribution']
        dockerconfig = root / 'anonymous-docker'
        dockerconfig.mkdir(exist_ok=True)
        assert not list(dockerconfig.iterdir()), 'anonymous Docker configuration is not empty'
        logged('anonymous-runtime-pull.log', ['docker', 'pull', runtime['image_reference']], 600, env)
        image = inspect(runtime['image_reference'])
        model = home / '.local/share/omp-ninfer/qwen3_8_27b.ninfer'
        assert model.stat().st_size == runtime['model_bytes'] and digest(model) == runtime['model_sha256']
        archive = root / dist['asset_url'].rsplit('/', 1)[-1]
        if not archive.exists():
            run(['curl', '--fail', '--location', '--silent', '--show-error', '--output', archive, dist['asset_url']], 300)
        assert digest(archive) == dist['archive_sha256']
        package = root / archive.name.removesuffix('.tar.gz')
        if not package.exists():
            run(['tar', '-xzf', archive, '-C', root], 60)
        linuxhome = root / 'linux-home'
        linuxhome.mkdir(exist_ok=True)
        clientenv = dict(os.environ, HOME=str(linuxhome), XDG_DATA_HOME=str(linuxhome / '.local/share'), XDG_CONFIG_HOME=str(linuxhome / '.config'), XDG_BIN_HOME=str(linuxhome / '.local/bin'))
        launcher = linuxhome / '.local/bin/omp'
        if not launcher.exists():
            run(['sh', package / 'install.sh'], 60, clientenv)
        installed = list((linuxhome / '.local/share/omp/releases').glob('*/omp'))
        assert len(installed) == 1 and digest(installed[0]) == dist['binary_sha256']
        logged('linux-preflight.log', [sys.executable, root / 'omp-client-probe.py', '--release', a.release, '--candidate', a.candidate, '--phase', 'preflight', '--output', root / 'linux-structured', '--binary', launcher, '--clone', clone, '--platform', 'linux-x64-wsl2', '--profile', 'linux-docker-local'], 90, clientenv)
        save('host-preflight.json', {'status': 'passed', 'completed_utc': now(), 'baseline': baseline(), 'runtime_image': runtime['image_reference'], 'runtime_repo_digests': image['RepoDigests'], 'model_sha256': digest(model), 'client_archive_sha256': digest(archive), 'client_binary_sha256': digest(installed[0]), 'wsl_environment_preserved': True})
    elif a.action == 'begin':
        assert not (root / 'baseline.json').exists(), 'window already attempted; no implicit retry'
        assert 0 < a.restore_after_seconds <= 3000
        b = baseline(); b['start_epoch'] = time.time(); b['restore_deadline_epoch'] = time.time() + a.restore_after_seconds
        save('baseline.json', b)
        with (root / 'watchdog.log').open('w') as log:
            command = [sys.executable, __file__, *sys.argv[1:]]
            command[command.index('begin')] = 'watchdog'
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        save('watchdog.json', {'pid': process.pid, 'restore_deadline_epoch': b['restore_deadline_epoch']})
        try:
            key.rename(root / 'original-api-key')
            for label, path in (('logs', logs), ('checkpoints', checkpoints)):
                path.rename(root / ('original-' + label))
                path.mkdir(mode=0o700)
            run(['git', '-C', checkout, 'fetch', '-q', str(clone), a.candidate], 90)
            run(['git', '-C', checkout, 'checkout', '-q', '--detach', a.candidate])
            logged('stop-production.log', ['bash', Path(a.window_dir) / 'window.sh', 'stop-production'], 180)
        except BaseException:
            restore()
            raise
    elif a.action == 'watchdog':
        b = json.loads((root / 'baseline.json').read_text())
        while time.time() < b['restore_deadline_epoch']:
            if (root / 'restoration.json').exists():
                return
            time.sleep(5)
        restore()
    elif a.action == 'restore':
        restore()
    elif a.action == 'host-route':
        logged('host-route.log', ['bash', clone / 'scripts/hosts/run-documented-route.sh', root / 'host-bundle', clone, root / 'host-route.json'], 1200, env)
    elif a.action == 'setup':
        # Explicit completion-window setup, not another documented-route acceptance.
        # Reuse the original documented key only inside this same trusted host boundary.
        shutil.copy2(root / 'original-api-key', key)
        logged('beta-setup.log', [clone / 'examples/manual-tunnel/start-ninfer.sh',
               '--model', home / '.local/share/omp-ninfer/qwen3_8_27b.ninfer',
               '--api-key-file', key, '--log-dir', logs, '--checkpoint-dir', checkpoints], 1200, env)
        save('setup.json', {'status': 'passed', 'kind': 'published launcher setup; no route runner invoked', 'candidate': a.candidate, 'completed_utc': now()})
    elif a.action == 'identity':
        d = inspect('omp-ninfer-beta')
        image = inspect(d['Image'])
        binary = run(['docker', 'exec', 'omp-ninfer-beta', 'sha256sum', '/usr/local/bin/ninfer-serve']).split()[0]
        request = urllib.request.Request('http://127.0.0.1:18089/v1/ninfer/status', headers={'Authorization': 'Bearer ' + key.read_text().strip()})
        with urllib.request.urlopen(request, timeout=15) as r:
            status = json.load(r)
        save('runtime-observed.json', {'timestamp': now(), 'configured_image': d['Config']['Image'], 'repo_digests': image['RepoDigests'], 'image_id': d['Image'], 'binary_sha256': binary, 'served': status})
    elif a.action in ('beta-start', 'beta-stop'):
        run(['docker', 'start' if a.action == 'beta-start' else 'stop', 'omp-ninfer-beta'], 150)
        if a.action == 'beta-start':
            for _ in range(150):
                try:
                    if health(18089).get('status') == 'ok':
                        break
                except Exception:
                    pass
                time.sleep(2)
            assert health(18089)['status'] == 'ok'
    else:
        linuxhome = root / 'linux-home'
        agent = linuxhome / '.omp/agent'
        agent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not (agent / 'models.yml').exists():
            shutil.copyfile(clone / 'examples/manual-tunnel/models.fragment.yml', agent / 'models.yml')
            shutil.copyfile(clone / 'examples/manual-tunnel/fail-closed.yml', agent / 'config.yml')
            shutil.copyfile(key, agent / 'ninfer-beta.key')
            os.chmod(agent / 'ninfer-beta.key', 0o600)
        clientenv = dict(os.environ, HOME=str(linuxhome), XDG_DATA_HOME=str(linuxhome / '.local/share'), XDG_CONFIG_HOME=str(linuxhome / '.config'), XDG_BIN_HOME=str(linuxhome / '.local/bin'))
        phase = 'live' if a.action == 'linux-live' else 'outage'
        logged('linux-' + phase + '.log', [sys.executable, root / 'omp-client-probe.py', '--release', a.release, '--candidate', a.candidate, '--phase', phase, '--output', root / 'linux-structured', '--binary', linuxhome / '.local/bin/omp', '--clone', clone, '--platform', 'linux-x64-wsl2', '--profile', 'linux-docker-local', '--key-file', agent / 'ninfer-beta.key'], 850, clientenv)
    print(json.dumps({'action': a.action, 'status': 'passed', 'workspace': str(root)}))


if __name__ == '__main__':
    main()
