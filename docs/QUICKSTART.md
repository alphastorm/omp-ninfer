# Early-access quickstart

This is the supported `v0.1.0-beta.1` path: OMP on Apple-silicon macOS, NInfer on one
user-controlled Linux or WSL2 RTX 5090 host, and an authenticated SSH local forward between them.
It is deliberately manual. Do not use `omp appliance install` for this beta.

The checked-in manifest is currently an installable `candidate`. Invited testers must still stop
unless the product release tag exists and the ready contract succeeds from a clean clone of that
tag. Maintainers may use the exact candidate commit for the bounded external-install acceptance:

```sh
python3 scripts/verify_release.py --require-ready
```

That gate prevents these instructions from resolving an unpinned image or unfinished OMP package.
The only pre-tag exception is the bounded maintainer acceptance gate: it uses an exact public
`candidate` commit after every installable artifact is pinned, and must first pass
`python3 scripts/verify_release.py --require-installable`. A candidate is not an invited-tester
release and cannot be tagged until this quickstart succeeds and the observed result is bound into a
`ready` manifest.

## Prerequisites

**Mac**

- Apple silicon running the macOS version declared by the `omp-beta` cask;
- Homebrew and OpenSSH; and
- at least 1 GiB free for OMP and local state.

**Inference host**

- a single-user Linux or WSL2 environment owning one NVIDIA GeForce RTX 5090;
- a current NVIDIA driver, Docker with Linux host-network support, and NVIDIA Container Toolkit;
- OpenSSH access terminating in the same Linux/WSL namespace as Docker; and
- at least 40 GiB free for the 18,210,531,328-byte model, image, and logs.

The NInfer endpoint binds only to remote loopback. Never publish port `18089` on a LAN or public
interface. The first beta assumes both machines and local accounts are controlled by one trusted
owner.

## 1. Clone the exact release on both machines

After the prerelease is published, run this on the Mac and inference host:

```sh
git clone --branch v0.1.0-beta.1 --depth 1 \
  https://github.com/alphastorm/omp-ninfer.git
cd omp-ninfer
python3 scripts/verify_release.py --require-ready
```

Do not invite testers from moving `main`, an untagged archive, or a manifest whose status is
`draft` or `candidate`.
The bounded pre-tag acceptance instead checks out its recorded candidate commit in detached mode;
it must never use moving `main` as the tested identity.

## 2. Install the OMP beta on the Mac

```sh
(
set -euo pipefail
brew tap alphastorm/omp
brew update
CASK_REVISION=$(python3 -c \
  'import json; print(json.load(open("releases/v0.1.0-beta.1/manifest.json"))["components"]["omp"]["homebrew_cask_revision"])')
TAP_ROOT=$(brew --repository alphastorm/omp)
git -C "$TAP_ROOT" fetch --quiet origin "$CASK_REVISION"
PINNED_CASK_SHA=$(git -C "$TAP_ROOT" show "$CASK_REVISION:Casks/omp-beta.rb" | shasum -a 256 | cut -d ' ' -f 1)
CURRENT_CASK_SHA=$(shasum -a 256 "$TAP_ROOT/Casks/omp-beta.rb" | cut -d ' ' -f 1)
test "$CURRENT_CASK_SHA" = "$PINNED_CASK_SHA"

if brew list --cask omp >/dev/null 2>&1; then
  brew uninstall --cask omp
fi
HOMEBREW_NO_AUTO_UPDATE=1 brew install --cask omp-beta
omp --version
)
```

The stable and beta casks deliberately conflict because both own the same immutable release root and
`~/.local/bin/omp` launcher. The content comparison prevents a moving tap from substituting a
different beta cask after the manifest was cut; `HOMEBREW_NO_AUTO_UPDATE` keeps it fixed through
installation. Do not manually overwrite the stable binary. To return to stable, uninstall
`omp-beta` and reinstall `omp`.

## 3. Prepare the model and key on the inference host

From the release clone:

```sh
ROOT="$HOME/.local/share/omp-ninfer"
STATE="$HOME/.config/omp-ninfer"
LOGS="$HOME/.local/state/omp-ninfer"
install -d -m 700 "$ROOT" "$STATE" "$LOGS"

MODEL_URL=$(python3 -c \
  'import json; print(json.load(open("releases/v0.1.0-beta.1/manifest.json"))["components"]["model"]["artifact_url"])')
MODEL_BYTES=$(python3 -c \
  'import json; print(json.load(open("releases/v0.1.0-beta.1/manifest.json"))["components"]["model"]["artifact_bytes"])')
MODEL_SHA256=$(python3 -c \
  'import json; print(json.load(open("releases/v0.1.0-beta.1/manifest.json"))["components"]["model"]["artifact_sha256"])')
MODEL="$ROOT/qwen3_8_27b.ninfer"

curl --fail --location --continue-at - --output "$MODEL" "$MODEL_URL"
test "$(stat -c %s "$MODEL")" = "$MODEL_BYTES"
printf '%s  %s\n' "$MODEL_SHA256" "$MODEL" | sha256sum --check --strict

umask 077
openssl rand -hex 32 > "$STATE/api-key"
chmod 600 "$STATE/api-key"
```

The artifact is pinned to one Hugging Face revision, byte count, and SHA-256. A checksum mismatch is
a hard stop; do not rename or reuse the partial file as a successful download.

## 4. Start NInfer on the inference host

```sh
./examples/manual-tunnel/start-ninfer.sh \
  --model "$MODEL" \
  --api-key-file "$STATE/api-key" \
  --log-dir "$LOGS"
```

The launcher:

- refuses a draft manifest;
- pulls the digest-pinned image;
- checks the model and `ninfer-serve` binary hashes;
- starts one owned `omp-ninfer-beta` container with restart policy `no`;
- mounts the model and API key read-only;
- shares the Linux/WSL2 host network namespace and binds `127.0.0.1:18089` only; and
- waits for authenticated status to match source, binary, model, configuration, profile, and runtime
  fields.

It deliberately leaves a failed container in place for `docker logs omp-ninfer-beta`. Stop and
remove only the correctly labelled beta container with:

```sh
./examples/manual-tunnel/stop-ninfer.sh
```

The server receives the key through a read-only secret mount and an in-container shell expansion,
so the key is not embedded in the Docker configuration or host shell history. The resulting server
process argument is visible to root inside the trusted container/host boundary; this is not a
multi-tenant secret-isolation design.

## 5. Open the tunnel from the Mac

In a dedicated terminal inside the Mac release clone:

```sh
./examples/manual-tunnel/open-tunnel.sh USER@RUNTIME_HOST
```

Replace the destination with the SSH user and host that terminate in the Linux/WSL namespace owning
Docker. Keep this process running. `ExitOnForwardFailure` prevents a false-green tunnel when local
port `18089` is occupied; keepalive options make a dead route observable.

## 6. Install the same key on the Mac

In another Mac terminal:

```sh
install -d -m 700 "$HOME/.omp/agent"
umask 077
ssh USER@RUNTIME_HOST 'cat "$HOME/.config/omp-ninfer/api-key"' \
  > "$HOME/.omp/agent/ninfer-beta.key"
chmod 600 "$HOME/.omp/agent/ninfer-beta.key"
```

This streams the secret inside SSH and does not print it. Use the exact destination from the tunnel.
Do not paste the key into YAML, shell history, an issue, or a support bundle.

## 7. Add the OMP provider

If `~/.omp/agent/models.yml` does not exist:

```sh
install -m 600 examples/manual-tunnel/models.fragment.yml \
  "$HOME/.omp/agent/models.yml"
```

If it already exists, merge only the `providers.ninfer-beta` mapping from
[`models.fragment.yml`](../examples/manual-tunnel/models.fragment.yml). Do not overwrite existing
providers or model definitions. The key remains an executable secret reference:

```yaml
apiKey: '!cat "$HOME/.omp/agent/ninfer-beta.key"'
```

Install the supplied fail-closed settings into the launcher-owned default config whenever exercising
the beta. If the file already exists, merge only the `retry` mapping instead of overwriting unrelated
settings:

```sh
install -m 600 examples/manual-tunnel/fail-closed.yml \
  "$HOME/.omp/agent/config.yml"
omp --model ninfer-beta/local-max
```

The sealed launcher owns config selection and deliberately rejects `--config`; the default config plus
the explicit provider/model disable model fallback. A tunnel or runtime failure must be an error, not a
switch to a cloud model.

## 8. Early-access acceptance

Run these checks in order and record only pass/fail plus the content-safe identities from the NInfer
launcher.

### Text and tool turn

```sh
SMOKE=$(mktemp -d)
printf 'OMP_NINFER_TOOL_OK\n' > "$SMOKE/marker.txt"
cd "$SMOKE"
omp --model ninfer-beta/local-max \
  "Use a file-reading tool to read marker.txt, then report its exact single line."
```

The turn must use the local model and successfully execute the file-reading tool. Model wording is
not a numerical oracle; the observed tool result is the contract.

### Image input

From a directory containing a non-sensitive PNG or JPEG:

```sh
omp --model ninfer-beta/local-max \
  @sample.png "Describe the visible image in one sentence."
```

A completed response proves the configured Vision route is reachable. Do not use private screenshots
in an issue.

### Stateful follow-up and OMP resume

Start an interactive session:

```sh
omp --model ninfer-beta/local-max \
  "Remember the nonce COBALT-493817 for my next turn."
```

In the same session, ask for the nonce. Exit OMP normally, then resume that session:

```sh
omp --model ninfer-beta/local-max --continue \
  "Return the nonce from the prior turn."
```

The transcript remains authoritative. This checks ordinary OMP exit/resume with NInfer stateful
Responses while the NInfer process remains alive; it does **not** claim NInfer process-restart
continuation.

### Fail closed

Stop the tunnel with `Ctrl-C`, then run:

```sh
omp --no-session --max-time 20s \
  --model ninfer-beta/local-max \
  "Return LOCAL_ONLY."
```

Expected result: a connection failure and no model response. Any cloud-provider request is a release
failure. Restart the tunnel only after observing the failure.

## 9. Send feedback

Use the repository issue forms. Include:

- release and profile IDs;
- OS, GPU name, VRAM, driver, Docker, and OMP versions;
- the failing step and content-safe error; and
- whether the route was fresh, resumed, or tunnel-disconnected.

Exclude API keys, usernames, hostnames, IP addresses, private paths, prompts, model output, raw
request logs, and Docker inspection dumps. See [Troubleshooting](TROUBLESHOOTING.md) before attaching
anything.
