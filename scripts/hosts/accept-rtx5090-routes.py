#!/usr/bin/env python3
"""Run published 5090 documented routes and isolated platform acceptance.

Preflight prepares private workspaces without opening a production window.
Window always invokes independent restoration in finally; a detached WSL
watchdog begins restoration at 50 minutes, reserving ten minutes of the cap.
No automatic acceptance retries. --dry-run is entirely read-only/no-effect.
Only JSON receipts and named private logs are collected, never credential files.
"""
import argparse
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
import urllib.request


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for data in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


MARKER = 'OMP_NINFER_TOOL_OK'
NONCE = 'COBALT-493817'
MARKER_TOKEN = re.compile(r'(?<![A-Z0-9_])' + MARKER + r'(?![A-Z0-9_])')


def windows_route_answers(lines):
    """What the documented Windows commands visibly returned. The tool prompt asks the model to
    report the file's line, which it may quote or format, so only the marker token is required,
    as on the other routes; the structured probe separately requires its whole answer exactly.
    The resume prompt asks for the nonce alone, so that line must be exact."""
    assert any(MARKER_TOKEN.search(line) for line in lines), 'Windows route did not visibly return the tool marker'
    assert any(line.strip() == NONCE for line in lines), 'Windows route did not visibly return exact nonce'
    return {'tool_marker_observed': True,
            'plain_stdout_exact_marker': any(line.strip() == MARKER for line in lines),
            'exact_nonce_line': True}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--action', choices=('preflight', 'window', 'windows-live-only', 'restore', 'collect', 'summarize'), required=True)
    for name in ('release', 'candidate', 'workspace', 'wsl-workspace', 'windows-workspace', 'production-image'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--wsl-host', default='nyc-pc-wsl')
    p.add_argument('--windows-host', default='nyc-pc')
    p.add_argument('--route-ssh-destination', default='Sunil@nyc-pc')
    p.add_argument('--attempt', choices=('initial', 'corrected'), default='initial')
    p.add_argument('--prior-workspace', help='Restored initial evidence root; required for a corrected attempt')
    p.add_argument('--windows-evidence', help='Explicitly authorized Windows-only completion evidence root for final aggregation')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    if not PureWindowsPath(a.windows_workspace).is_absolute():
        p.error('--windows-workspace must be absolute (prefer C:/Users/... to avoid shell escaping)')
    if a.dry_run:
        phases = ['hold', 'stop production', 'published launcher setup (not a route run)', 'Windows structured live and outage', 'independent restoration', 'collect'] if a.action == 'windows-live-only' else ['preflight', 'hold', 'stop production', 'host route', 'Linux live/outage', 'Mac route/live/outage', 'Windows live/route/outage', 'independent restoration', 'collect']
        print(json.dumps({'status': 'dry-run', 'release': a.release, 'candidate': a.candidate, 'action': a.action, 'effects': 'none',
                          'client_install': {'lane': 'rtx5090-macos-client', 'step': 'client-install',
                                             'launcher': '$HOME/.local/bin/omp', 'distribution_kind': 'upstream-release'},
                          'phases': phases, 'downtime_cap_seconds': 3600}))
        return
    root = Path(a.workspace).resolve()
    source = Path(__file__).resolve().parent
    clone = root / 'candidate'
    routehome = root / 'mac-home'
    macclone = routehome / 'omp-ninfer'
    windows = a.windows_workspace
    wsl = a.wsl_workspace
    watchdog_seconds = 3000
    timings = json.loads((root / 'timings.json').read_text()) if (root / 'timings.json').exists() else []
    def save(name, value):
        (root / name).write_text(json.dumps(value, indent=2) + '\n')
    def run(argv, label, timeout=120, env=None, capture=False, cwd=None):
        start = time.monotonic()
        started = now()
        if capture:
            r = subprocess.run([str(x) for x in argv], capture_output=True, text=True, timeout=timeout, env=env, cwd=cwd)
        else:
            with (root / (label + '.log')).open('w') as log:
                r = subprocess.run([str(x) for x in argv], stdout=log, stderr=subprocess.STDOUT, timeout=timeout, env=env, cwd=cwd)
        timings.append({'phase': label, 'started_utc': started, 'seconds': round(time.monotonic() - start, 3), 'exit': r.returncode})
        save('timings.json', timings)
        if r.returncode:
            raise RuntimeError(label + ' exited ' + str(r.returncode) + '; inspect private log')
        return r.stdout.strip() if capture else None
    def remote(argv, label, timeout=120):
        return run(['ssh', '-o', 'BatchMode=yes', a.wsl_host, shlex.join([str(x) for x in argv])], label, timeout)
    def host(action, timeout=120, dry=False):
        args = ['python3', wsl + '/accept-rtx5090-host.py', '--action', action, '--release', a.release, '--candidate', a.candidate,
                '--workspace', wsl, '--windows-workspace', windows, '--production-image', a.production_image, '--restore-after-seconds', str(watchdog_seconds)]
        if dry:
            args.append('--dry-run')
        return remote(args, 'host-' + action + ('-dry-run' if dry else ''), timeout)
    def win(action, timeout=120, dry=False):
        quote = lambda s: "'" + str(s).replace("'", "''") + "'"
        ps = "& ([scriptblock]::Create([IO.File]::ReadAllText(" + quote(windows + '\\accept-windows-client.ps1') + "))) -Action " + action + " -Workspace " + quote(windows) + " -Release " + quote(a.release) + " -Candidate " + quote(a.candidate)
        if dry:
            ps += ' -DryRun'
        # Only owner-hold operations use bypass. The documented runner is launched as text.
        args = ['powershell', '-NoProfile']
        if action in ('Hold', 'Release'):
            args += ['-ExecutionPolicy', 'Bypass']
        args += ['-EncodedCommand', base64.b64encode(ps.encode('utf-16le')).decode()]
        return run(['ssh', '-o', 'BatchMode=yes', a.windows_host, ' '.join(args)], 'windows-' + action.lower() + ('-dry-run' if dry else ''), timeout)
    def isolated(home):
        (home / 'tmp').mkdir(parents=True, exist_ok=True)
        return dict(os.environ, HOME=str(home), XDG_DATA_HOME=str(home / '.local/share'), XDG_CONFIG_HOME=str(home / '.config'),
                    XDG_BIN_HOME=str(home / '.local/bin'), XDG_CACHE_HOME=str(home / '.cache'),
                    TMPDIR=str(home / 'tmp') + '/',
                    PATH=str(home / '.local/bin') + ':' + os.environ['PATH'])
    def macprobe(phase, home=routehome):
        args = [sys.executable, source / 'omp-client-probe.py', '--release', a.release, '--candidate', a.candidate, '--phase', phase,
                '--output', root / 'mac-structured', '--binary', home / '.local/bin/omp', '--clone', macclone,
                '--platform', 'macos-arm64', '--profile', 'darwin-remote-ssh', '--key-file', home / '.omp/agent/ninfer-beta.key', '--vision-image', macclone / 'assets/icon-512.png']
        run(args, 'mac-' + phase, 850, isolated(home))
    def freeport():
        with socket.socket() as s:
            s.bind(('127.0.0.1', 18089))
    def collect(narrow=False):
        # Explicit allowlist prevents backups, keys, installed profiles, and configs escaping.
        missing = []
        def transfer(argv, label, timeout=120):
            try:
                run(argv, label, timeout)
            except RuntimeError as error:
                missing.append(str(error))
        host_files = ['host-preflight.json', 'baseline.json', 'restoration.json', 'runtime-observed.json', 'watchdog.json', 'production-restore.log']
        host_files += ['setup.json', 'beta-setup.log'] if narrow else ['host-route.json', 'host-route.log']
        for name in host_files:
            transfer(['scp', '-q', a.wsl_host + ':' + wsl + '/' + name, root / name], 'collect-' + name, 90)
        for directory in (() if narrow else ('host-bundle', 'linux-structured')):
            transfer(['scp', '-q', '-r', a.wsl_host + ':' + wsl + '/' + directory, root / ('remote-' + directory)], 'collect-' + directory, 120)
        windows_files = ['windows-preflight.json', 'windows-baseline.json', 'windows-final.json']
        if not narrow:
            windows_files.append('windows-route.json')
        for name in windows_files:
            transfer(['scp', '-q', a.windows_host + ':' + windows.replace('\\', '/') + '/' + name, root / name], 'collect-' + name, 90)
        transfer(['scp', '-q', '-r', a.windows_host + ':' + windows.replace('\\', '/') + '/windows-structured', root / 'windows-structured'], 'collect-windows-structured', 120)
        save('collection.json', {'completed_utc': now(), 'missing': missing})
    def summarize():
        result = {'release': a.release, 'candidate': a.candidate, 'status': 'passed', 'completed_utc': now(), 'routes': {}, 'clients': {}, 'timings': timings, 'corrections': [],
                  'new_scripts': [str(source / f) for f in ('accept-rtx5090-routes.py', 'accept-rtx5090-host.py', 'accept-windows-client.ps1', 'omp-client-probe.py')]}
        if a.prior_workspace:
            result['corrections'] = json.loads((Path(a.prior_workspace) / 'corrections.json').read_text())
        result['script_sha256'] = {path: sha(path) for path in result['new_scripts']}
        for label, count in (('host', 2), ('mac', 10), ('windows', 5)):
            receipt = json.loads((root / (label + '-route.json')).read_text())
            manifest = json.loads((root / (label + '-bundle/manifest.json')).read_text())
            assert receipt['status'] == 'passed' and len(receipt['steps']) == count
            assert receipt['document_sha256'] == manifest['document_sha256']
            assert all(step['block_sha256'] == step['executed_sha256'] == expected['sha256'] and step['status'] in ('passed', 'substituted') for step, expected in zip(receipt['steps'], manifest['steps']))
            result['routes'][label] = {'path': str(root / (label + '-route.json')), 'receipt': receipt}
        for label, folder in (('linux', 'remote-linux-structured'), ('mac', 'mac-structured'), ('windows', 'windows-structured')):
            evidence_root = Path(a.windows_evidence) if label == 'windows' and a.windows_evidence else root
            receipt = json.loads((evidence_root / folder / 'receipt.json').read_text())
            receipt['receipt_path'] = str(evidence_root / folder / 'receipt.json')
            assert receipt['status'] == 'passed'
            stream_audit = {}
            for phase in ('tool', 'state', 'continuation', 'vision', 'fail-closed'):
                if phase not in receipt['phases']:
                    continue
                providers, models = set(), set()
                images = 0
                raw = (evidence_root / folder / (phase + '.jsonl')).read_bytes()
                encoding = 'utf-8'
                try:
                    transcript = raw.decode(encoding)
                except UnicodeDecodeError:
                    # Preserve earlier Windows-native bytes written in its default locale.
                    # New probe output explicitly uses UTF-8; never rewrite historical evidence.
                    assert label == 'windows', 'non-Windows transcript is not UTF-8'
                    encoding = 'cp1252'
                    transcript = raw.decode(encoding)
                for line in transcript.splitlines():
                    try:
                        stack = [json.loads(line)]
                    except ValueError:
                        continue
                    while stack:
                        node = stack.pop()
                        if isinstance(node, list):
                            stack.extend(node)
                        elif isinstance(node, dict):
                            images += node.get('type') == 'image'
                            if isinstance(node.get('provider'), str):
                                providers.add(node['provider'])
                            if isinstance(node.get('model'), str):
                                models.add(node['model'])
                            stack.extend(node.values())
                assert providers == {'ninfer-beta'} and models and models <= {'q38-ninfer'}, label + '/' + phase + ': unexpected provider/model record'
                stream_audit[phase] = {'providers': sorted(providers), 'models': sorted(models), 'input_image_records': images, 'only_selected_provider_and_model': True, 'decode_encoding': encoding, 'transcript_sha256': hashlib.sha256(raw).hexdigest()}
            receipt['full_stream_audit'] = stream_audit
            result['clients'][label] = receipt
        runtime = json.loads((root / 'runtime-observed.json').read_text())
        authority = json.loads((clone / 'compatibility.json').read_text())
        expected = next(v['runtime'] for v in authority['profiles'] if v['id'] == 'linux-docker-local')
        assert runtime['configured_image'] == expected['image_reference'] and expected['image_reference'] in runtime['repo_digests']
        assert runtime['binary_sha256'] == expected['server_binary_sha256']
        result['observed_runtime'] = runtime
        for label, receipt in result['clients'].items():
            receipt['live_acceptance'].update({'runtime_image_digest': runtime['configured_image'].split('@', 1)[1], 'runtime_variant': 'rtx5090-container', 'profile_runtime_qualified_by_this_receipt': False})
            if label == 'linux':
                receipt['live_acceptance']['execution_context'] = receipt['execution_context']
        result['restoration'] = json.loads((root / 'restoration.json').read_text())
        before, after = [json.loads((root / name).read_text(encoding='utf-8-sig')) for name in ('windows-baseline.json', 'windows-final.json')]
        for field in ('markers', 'tasks'):
            assert before[field] == after[field], 'Windows ' + field + ' changed'
        result['restoration']['windows_markers_tasks_unchanged'] = True
        result['restoration']['windows_health'] = after['windows_health18088']
        assert result['restoration']['window_seconds'] <= 3600
        if a.windows_evidence:
            completion = Path(a.windows_evidence)
            completed = json.loads((completion / 'completion-summary.json').read_text())
            assert completed['status'] == 'passed'
            result['previous_window_restoration'] = result['restoration']
            result['restoration'] = completed['restoration']
            result['windows_completion_setup'] = completed['setup']
            result['timings'].extend(json.loads((completion / 'timings.json').read_text()))
            prior_seconds = json.loads((Path(a.prior_workspace) / 'restoration.json').read_text())['window_seconds'] if a.prior_workspace else 0
            result['aggregate_window_seconds'] = prior_seconds + result['previous_window_restoration']['window_seconds'] + result['restoration']['window_seconds']
            assert result['aggregate_window_seconds'] < 3600
        smoke = list((routehome / 'tmp').glob('*/durable.txt'))
        collected_smoke = root / 'mac-documented-smoke'
        if not smoke and (collected_smoke / 'durable.txt').exists():
            smoke = [collected_smoke / 'durable.txt']
        if not smoke:
            # Stock macOS mktemp may choose Darwin's per-user temp root despite TMPDIR.
            # Match both this route's time interval and exact concatenated candidate context
            # before moving only the directory this run created into the private evidence root.
            temp_root = Path(subprocess.check_output(['getconf', 'DARWIN_USER_TEMP_DIR'], text=True).strip())
            context_hash = hashlib.sha256()
            for relative in ('docs/BENCHMARKS.md', 'README.md', 'docs/ARCHITECTURE.md', 'docs/PERFORMANCE.md', 'CHANGELOG.md'):
                context_hash.update((macclone / relative).read_bytes())
            route = result['routes']['mac']['receipt']
            start = datetime.datetime.fromisoformat(route['started_utc'].replace('Z', '+00:00')).timestamp()
            end = datetime.datetime.fromisoformat(route['completed_utc'].replace('Z', '+00:00')).timestamp() + 2
            matches = [path for path in temp_root.glob('tmp.*/durable.txt') if start <= path.stat().st_mtime <= end and (path.parent / 'context.md').is_file() and sha(path.parent / 'context.md') == context_hash.hexdigest()]
            assert len(matches) == 1, 'cannot uniquely bind Mac smoke directory to this route'
            shutil.move(str(matches[0].parent), str(collected_smoke))
            smoke = [collected_smoke / 'durable.txt']
        assert len(smoke) == 1 and smoke[0].read_text().strip() == 'COBALT-493817', 'documented restart did not return exact nonce'
        assert (smoke[0].parent / 'resume.txt').read_text().strip() == 'COBALT-493817'
        tool_output = (smoke[0].parent / 'tool.txt').read_text().strip()
        assert MARKER_TOKEN.search(tool_output), 'documented tool marker absent'
        result['routes']['mac']['tool_marker_observed'] = True
        result['routes']['mac']['plain_stdout_exact_marker'] = tool_output == 'OMP_NINFER_TOOL_OK'
        result['routes']['mac']['smoke_artifact_directory'] = str(smoke[0].parent)
        result['routes']['mac']['exact_restart_nonce'] = True
        result['clients']['mac']['live_acceptance']['documented_server_restart_nonce_returned'] = True
        result['routes']['windows'].update(windows_route_answers((root / 'windows-route.log').read_text().splitlines()))
        result['private_root'] = str(root)
        save('final-summary.json', result)
        return result
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if a.action == 'preflight':
        if not clone.exists():
            run(['git', 'clone', '-q', 'https://github.com/alphastorm/omp-ninfer.git', clone], 'clone', 180)
            run(['git', '-C', clone, 'checkout', '-q', a.candidate], 'checkout')
        assert run(['git', '-C', clone, 'rev-parse', 'HEAD'], 'candidate-identity', capture=True) == a.candidate
        assert not run(['git', '-C', clone, 'status', '--porcelain'], 'candidate-clean', capture=True)
        run([sys.executable, clone / 'scripts/verify_release.py', '--release', a.release, '--require-installable'], 'verify-candidate')
        for label, lane in (('host', 'rtx5090-container-host'), ('mac', 'rtx5090-macos-client'), ('windows', 'rtx5090-windows-client')):
            if not (root / (label + '-bundle')).exists():
                run([sys.executable, clone / 'scripts/documented_route.py', 'bundle', '--lane', lane, '--output', root / (label + '-bundle')], 'bundle-' + label)
        routehome.mkdir(exist_ok=True)
        if not macclone.exists():
            run(['git', 'clone', '-q', '--no-hardlinks', clone, macclone], 'mac-clone')
            run(['git', '-C', macclone, 'checkout', '-q', a.candidate], 'mac-checkout')
        comp = json.loads((clone / 'compatibility.json').read_text())
        dist = next(v['client_distribution'] for v in comp['profiles'] if v['id'] == 'darwin-remote-ssh')
        assert dist['distribution_kind'] == 'upstream-release', 'stock upstream client required'
        bundle = root / 'mac-bundle'
        install = next(step for step in json.loads((bundle / 'manifest.json').read_text())['steps'] if step['slug'] == 'client-install')
        assert sha(bundle / install['file']) == install['sha256'], 'client-install block differs from bundle'
        prehome = root / 'mac-preflight-home'
        prehome.mkdir(exist_ok=True)
        run(['bash', bundle / install['file']], 'mac-install-preflight', 300, env=isolated(prehome), cwd=prehome)
        asset = prehome / dist['asset_name']
        binary = prehome / '.local/bin/omp'
        assert sha(asset) == dist['asset_sha256'], 'published client asset checksum mismatch'
        assert sha(binary) == dist['binary_sha256'], 'installed client binary checksum mismatch'
        assert shutil.which('sha256sum') and shutil.which('ssh')
        freeport()
        macprobe('preflight', prehome)
        remote(['mkdir', '-p', wsl], 'wsl-private-root')
        create = '$null=New-Item -ItemType Directory -Force -Path ' + "'" + windows.replace("'", "''") + "'"
        run(['ssh', a.windows_host, 'powershell -NoProfile -EncodedCommand ' + base64.b64encode(create.encode('utf-16le')).decode()], 'windows-private-root')
        for name in ('accept-rtx5090-host.py', 'omp-client-probe.py'):
            run(['scp', '-q', source / name, a.wsl_host + ':' + wsl + '/' + name], 'stage-wsl-' + name)
        for name in ('accept-windows-client.ps1', 'omp-client-probe.py'):
            run(['scp', '-q', source / name, a.windows_host + ':' + windows.replace('\\', '/') + '/' + name], 'stage-windows-' + name)
        win('Preflight', 600)
        host('preflight', 900)
        host('restore', dry=True)
        win('Release', dry=True)
        save('preflight.json', {'status': 'passed', 'release': a.release, 'candidate': a.candidate, 'completed_utc': now(),
             'mac_asset_url': dist['asset_url'], 'mac_asset_sha256': sha(asset), 'mac_binary_sha256': sha(binary), 'bundles': {label: json.loads((root / (label + '-bundle/manifest.json')).read_text()) for label in ('host', 'mac', 'windows')}})
    elif a.action == 'windows-live-only':
        assert json.loads((root / 'preflight.json').read_text())['status'] == 'passed'
        assert a.prior_workspace, 'completion requires the restored route evidence root'
        prior = Path(a.prior_workspace)
        assert all(json.loads((prior / (label + '-route.json')).read_text())['status'] == 'passed' for label in ('host', 'mac', 'windows'))
        restored = json.loads((prior / 'restoration.json').read_text())
        assert restored['checkout_restored'] and restored['documented_key_restored'] and restored['beta_absent']
        spent = restored['window_seconds']
        earlier = json.loads((prior / 'window-attempt.json').read_text()).get('prior_workspace')
        if earlier:
            spent += json.loads((Path(earlier) / 'restoration.json').read_text())['window_seconds']
        watchdog_seconds = int(3600 - spent - 600)
        assert watchdog_seconds > 0, 'insufficient remaining envelope including restoration reserve'
        assert not (prior / 'windows-completion-attempt.json').exists(), 'Windows-only completion already attempted'
        (prior / 'windows-completion-attempt.json').write_text(json.dumps({'workspace': str(root), 'started_utc': now()}) + '\n')
        save('window-attempt.json', {'attempt': 'explicitly-authorized Windows first-live completion', 'started_utc': now(), 'no_documented_route_runner': True})
        held, error = False, None
        try:
            win('Hold'); held = True
            host('begin', 300)
            host('setup', 1250)
            host('identity')
            win('Live', 850)
            host('beta-stop', 180)
            win('Outage', 150)
        except BaseException as exc:
            error = str(exc)
            save('first-failure.json', {'boundary': error, 'timestamp': now()})
        finally:
            if held:
                host('restore', 700)
        collect(narrow=True)
        if error:
            raise RuntimeError(error + '; Windows-only completion restored before reporting failure')
        client = json.loads((root / 'windows-structured/receipt.json').read_text())
        assert client['status'] == 'passed'
        restored = json.loads((root / 'restoration.json').read_text())
        before, after = [json.loads((root / name).read_text(encoding='utf-8-sig')) for name in ('windows-baseline.json', 'windows-final.json')]
        assert before['markers'] == after['markers'] and before['tasks'] == after['tasks']
        restored.update({'windows_markers_tasks_unchanged': True, 'windows_health': after['windows_health18088']})
        save('completion-summary.json', {'status': 'passed', 'client': client, 'restoration': restored, 'setup': json.loads((root / 'setup.json').read_text()), 'runtime_observed': json.loads((root / 'runtime-observed.json').read_text())})
    elif a.action == 'summarize':
        summarize()
    elif a.action in ('restore', 'collect'):
        if a.action == 'restore':
            host('restore', 700)
        collect()
        if all((root / (label + '-route.json')).exists() for label in ('host', 'mac', 'windows')):
            summarize()
        else:
            save('partial-summary.json', {'status': 'restored-incomplete', 'restoration': json.loads((root / 'restoration.json').read_text()), 'first_failure': json.loads((root / 'first-failure.json').read_text()) if (root / 'first-failure.json').exists() else None})
    else:
        assert json.loads((root / 'preflight.json').read_text())['status'] == 'passed', 'preflight required'
        assert not (root / 'window-attempt.json').exists(), 'window already attempted; no implicit retry'
        freeport()
        if a.attempt == 'corrected':
            assert a.prior_workspace, 'corrected attempt requires its restored initial evidence'
            prior = Path(a.prior_workspace)
            assert json.loads((prior / 'window-attempt.json').read_text())['attempt'] == 'initial'
            restoration = json.loads((prior / 'restoration.json').read_text())
            assert restoration['checkout_restored'] and restoration['documented_key_restored'] and restoration['beta_absent']
            watchdog_seconds = int(3600 - restoration['window_seconds'] - 600)
            assert watchdog_seconds > 0, 'insufficient remaining envelope including restoration reserve'
            assert not (prior / 'corrected-attempt.json').exists(), 'the corrected attempt was already spent'
            (prior / 'corrected-attempt.json').write_text(json.dumps({'workspace': str(root), 'started_utc': now()}) + '\n')
        save('window-attempt.json', {'started_utc': now(), 'attempt': a.attempt, 'prior_workspace': a.prior_workspace})
        held = False
        started = False
        tunnel = None
        error = None
        try:
            win('Hold'); held = True
            host('begin', 300); started = True
            host('host-route', 1250)
            host('identity')
            host('linux-live', 850)
            host('beta-stop', 180)
            host('linux-outage', 120)
            host('beta-start', 360)
            env = isolated(routehome)
            env['ROUTE_SSH_DESTINATION'] = a.route_ssh_destination
            run(['bash', macclone / 'scripts/hosts/run-documented-route.sh', root / 'mac-bundle', macclone, root / 'mac-route.json'], 'mac-route', 1000, env)
            # The runner closed its documented forward. Prove the structured client fail-closed there.
            macprobe('outage')
            tunnel_log = (root / 'structured-tunnel.log').open('w')
            tunnel = subprocess.Popen(['ssh', '-N', '-o', 'BatchMode=yes', '-o', 'ExitOnForwardFailure=yes', '-o', 'ServerAliveInterval=10', '-L', '127.0.0.1:18089:127.0.0.1:18089', a.route_ssh_destination], stdout=tunnel_log, stderr=tunnel_log)
            for _ in range(30):
                if tunnel.poll() is not None:
                    raise RuntimeError('structured tunnel failed')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:18089/health', timeout=2) as r:
                        if r.status == 200:
                            break
                except Exception:
                    time.sleep(1)
            macprobe('live')
            # A prior passed outage plus live evidence completes this client's result without a second probe.
            path = root / 'mac-structured/receipt.json'
            receipt = json.loads(path.read_text())
            assert receipt['live_acceptance']['fail_closed']['no_model_response']
            receipt['status'] = 'passed'; path.write_text(json.dumps(receipt, indent=2) + '\n')
            tunnel.terminate(); tunnel.wait(timeout=15); tunnel = None; tunnel_log.close()
            win('Live', 850)
            # The documented fail-closed block removes beta, not merely stops it.
            # Capture structured live events first, then let the unchanged route own removal.
            win('Route', 850)
            win('Outage', 150)
        except BaseException as exc:
            error = str(exc)
            save('first-failure.json', {'boundary': error, 'timestamp': now()})
        finally:
            if tunnel is not None:
                tunnel.terminate(); tunnel.wait(timeout=15)
            if held:
                try:
                    host('restore', 700)
                except BaseException as restore_error:
                    save('restoration-error.json', {'error': str(restore_error), 'timestamp': now()})
                    raise
        collect()
        if error:
            raise RuntimeError(error + '; restoration completed before reporting failure')
        # Normalize combined phase status, never infer acceptance from process exit alone.
        path = root / 'windows-structured/receipt.json'
        receipt = json.loads(path.read_text())
        assert receipt['live_acceptance']['fail_closed']['no_model_response'] and receipt['live_acceptance']['continuation_exact_nonce']
        receipt['status'] = 'passed'; path.write_text(json.dumps(receipt, indent=2) + '\n')
        summarize()
    print(json.dumps({'status': 'passed', 'action': a.action, 'workspace': str(root)}))


if __name__ == '__main__':
    main()
