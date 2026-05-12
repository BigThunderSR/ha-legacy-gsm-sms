# CI & Code Quality Decisions

Rationale behind CI configuration choices, for contributor reference.

## Code Style (code-style.yml)

- **Black + isort** are enforced (blocking). Applied to entire codebase May 2026.
- **Flake8** is enforced (blocking) with a tuned ignore list in `setup.cfg`.
- Ignored flake8 rules are documented inline in `setup.cfg` with rationale.
- `temp-pavelve/` and `z-addon-old-test/` are excluded from all checks (legacy/experimental).

## Flake8 Ignore Rationale

| Code                         | Why ignored                                                                  |
| ---------------------------- | ---------------------------------------------------------------------------- |
| E203                         | Conflicts with black                                                         |
| W291, W292, W293             | Handled by black                                                             |
| E402                         | Intentional conditional/deferred imports                                     |
| E501                         | Black handles wrapping; remaining long lines are acceptable                  |
| E711, E722                   | Existing patterns; bare excepts are intentional for hardware fault tolerance |
| F401, F541, F811, F824, F841 | Dead code noise with no runtime impact                                       |

Rules kept active catch real bugs (e.g., `F821` undefined names).

### test-addon.yml Details

- Runs on Python 3.12 (matches the addon base image).
- Installs `requirements.txt` excluding `python-gammu` (requires C headers / `libgammu-dev` not available on GitHub-hosted runners).
- Path-filtered: only triggers when `addon-gsm-gateway/`, `addon-test-current/`, or the workflow itself changes.
- Two independent jobs: one per addon, so a failure in one doesn't skip the other.

### code-style.yml Details

- **Black** checks formatting — the entire codebase was reformatted with black 26.3.1 in May 2026.
- **isort** checks import ordering — uses `--profile black` for compatibility.
- **Flake8** catches real bugs (undefined names, syntax errors). Tuned ignore list in `setup.cfg` suppresses harmless patterns; see Flake8 Ignore Rationale above.
- All three are blocking — PRs cannot merge if any check fails.
- `temp-pavelve/` and `z-addon-old-test/` are excluded from all checks.

### builder.yml Details

- Detects which addons have changed files (Dockerfile, config.yaml, build.yaml, rootfs).
- Skips addons without an `image:` property in config.yaml (local-only builds).
- Builds via `home-assistant/builder` for amd64 and aarch64.
- On PRs: builds but does not publish. On push to main: builds and publishes to GHCR.
