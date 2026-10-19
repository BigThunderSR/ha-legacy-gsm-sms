# POC: Self-Hosted python-gammu Wheels for HACS Integration

> **Status:** Internal proof-of-concept — NOT shipped to users.
> **Date:** March 2026 (updated October 2026 — see [October 2026 Update](#october-2026-update))
> **Decision:** Shelved. The add-on approach is the supported path forward. This document preserves the technical findings in case the decision is revisited.

---

## October 2026 Update

The decision stays **shelved**. The original March findings below are kept unchanged as the historical record; this table shows what has changed since.

| Topic                                                          | Before (March 2026)                                                      | After (October 2026)                                                                                                                                                                                                           |
| -------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Upstream activity                                              | "Project has minimal activity"                                           | Active: python-gammu 3.3.0 → 3.5.0 and Gammu 1.43.3 → 1.45.0 released Jul–Sep 2026                                                                                                                                             |
| Latest versions                                                | python-gammu 3.2.6, Gammu 1.43.2                                         | python-gammu 3.5.0, Gammu 1.45.0                                                                                                                                                                                               |
| Minimum Gammu for python-gammu                                 | ≥ 1.43.0 (3.2.6)                                                         | ≥ 1.44.0 (3.5.0, `GAMMU_REQUIRED` in `setup.py`)                                                                                                                                                                               |
| Upstream binary wheels                                         | None for Linux                                                           | Since 3.3.0: `manylinux_2_28` x86_64/aarch64 wheels for cp310–cp314 with Gammu bundled. **No musllinux** — upstream's cibuildwheel config builds `cp3{10..14}-manylinux*` only, and its Gammu build script uses `dnf` only     |
| Who can install from PyPI without building                     | Nobody on Linux                                                          | glibc installs (e.g. HA Core on Debian/Ubuntu/Raspberry Pi OS). HA OS / HA Container (Alpine, musl) still cannot                                                                                                               |
| HA wheel index (`wheels.home-assistant.io/musllinux-index`)    | No longer maintained                                                     | Still only python-gammu 3.2.4 (cp311–cp313)                                                                                                                                                                                    |
| Alpine `gammu-dev`                                             | 1.42.0                                                                   | Still 1.42.0 on Alpine 3.22, 3.23 and 3.24                                                                                                                                                                                     |
| GCC 15 `-Wreturn-mismatch` error                               | Required a `setup.py` patch (3.2.6)                                      | **Not needed for 3.5.0** — builds cleanly with GCC 15.2.0 on Alpine 3.23 and 3.24 (verified Oct 2026)                                                                                                                          |
| Python 3.14 musllinux wheel                                    | Built from 3.2.6 with patch                                              | python-gammu 3.5.0 + Gammu 1.45.0 build to `cp314-musllinux_1_2` on Alpine 3.24 (Python 3.14.8), imports and reports versions correctly (verified Oct 2026, x86_64)                                                            |
| Build recipe maintenance                                       | Only in `build-gammu-wheels.yml` (manual, defaults still 3.2.6 / 1.43.2) | Same recipe now runs on every add-on build: `gammu-wheel` stage in `addon-gsm-gateway/Dockerfile` (add-on 2.21.0, PR #175). Downloads are SHA-256 pinned, and Renovate updates versions **and** hashes automatically (PR #176) |
| Upstream musllinux wheels (would remove the need to self-host) | Not considered                                                           | Considered and set aside — an upstream contribution is not expected to be accepted                                                                                                                                             |

**What this means if the decision is revisited:**

- The build no longer needs the GCC 15 patch, and the Dockerfile `gammu-wheel` stage is a tested, maintained reference for the wheel build (it only lacks the `python-gammu-ha` rename and PyPI publish steps).
- Any revival would target python-gammu ≥ 3.5.0 with Gammu ≥ 1.44, not the 3.2.6 / 1.43.2 versions in the steps below.
- The main reason for shelving is unchanged: owning a PyPI package that every HACS user installs on each restart.

---

## Background

Home Assistant 2026.3.0 / OS 17.1 upgraded to Python 3.14. The official `sms` integration was removed in HA 2025.12, and with it, HA stopped building pre-built `python-gammu` wheels at `wheels.home-assistant.io`. Since `python-gammu` is a C extension that requires `libgammu`, `gcc`, `cmake`, and other build tools not present in HAOS, the HACS integration can no longer install its dependency.

The HA core team cited this as having **no path forward**, which led to the deprecation.

## What We Proved

We demonstrated a working end-to-end path:

1. **Build gammu C library from source** in Docker (Alpine)
2. **Build python-gammu** against it
3. **Bundle all shared libraries** into the wheel via `auditwheel repair` (self-contained, zero system deps)
4. **Rename the distribution** to `python-gammu-ha` so HA's `is_installed()` version check works
5. **Publish to PyPI** as a normal package
6. `manifest.json` uses a simple `"requirements": ["python-gammu-ha==3.2.6"]`

The wheel was validated in a clean `python:3.14-alpine` container with no gammu headers or libraries installed — `import gammu` and `gammu.Version()` both work.

## Technical Discoveries

### 1. Alpine's gammu-dev is too old

Alpine's package repository has `gammu-dev` 1.42.0, but `python-gammu` 3.2.6 requires `>= 1.43.0` (checked via `pkg-config --atleast-version` in `setup.py` line 39). **Must build gammu 1.43.2 from source.**

Source URL: `https://github.com/gammu/gammu/releases/download/1.43.2/Gammu-1.43.2.tar.gz` (note: capital G)

cmake flags that work:

```bash
cmake .. -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_BUILD_TYPE=Release \
  -DWITH_BLUETOOTH=OFF -DBUILD_TESTING=OFF -DBUILD_GAMMU=OFF -DBUILD_DOC=OFF
make -j$(nproc) libGammu gsmsd
```

- `-DBUILD_TESTING=OFF` avoids a `libintl_gettext` linker error in test binaries
- `-DBUILD_GAMMU=OFF` skips the CLI binary (not needed)
- Target `gsmsd` (not `libgsmsd`) for the SMSD library

### 2. GCC 15 / Python 3.14 compiler error

`python-gammu` 3.2.6 fails to compile on GCC 15 with:

```bash
gammu.c:5458: error: 'return' with a value, in function returning void [-Wreturn-mismatch]
```

Root cause: The `BEGIN_PHONE_COMM` macro uses `return NULL` but `StateMachine_dealloc` returns `void`. GCC 15 promotes `-Wreturn-mismatch` to an error.

Fix:

```bash
sed -i '/extra_compile_args.append(flags)/a\    module.extra_compile_args.append("-Wno-error=return-mismatch")' setup.py
```

### 3. auditwheel makes it self-contained

A normal `pip wheel` build produces a wheel that dynamically links to system `libgammu.so`. On HAOS, that library doesn't exist.

`auditwheel repair` copies all non-system shared objects into the wheel itself:

```bash
pip install auditwheel patchelf
auditwheel repair /tmp/wheels/*.whl --plat musllinux_1_2_x86_64 -w /out/
```

Result: ~1.84 MiB wheel that includes `libgammu.so`, `libgsmsd.so`, and dependencies. Fully self-contained.

### 4. URL-based requirements cause reinstall on every HA restart

If `manifest.json` uses URL requirements (pointing to GitHub Releases), HA's `is_installed()` check always returns `False` — it can't match a URL string against locally installed packages. This means `uv pip install` runs on every restart (~1.8 MB download).

**This is a reliability problem**, not just cosmetic: users without internet on startup would have the integration fail to load, even though the wheel is already installed.

Solution: Publish to PyPI as `python-gammu-ha` and use a normal version-pinned requirement. HA's version check then works correctly.

### 5. Package rename via sed

`python-gammu` upstream owns the `python-gammu` name on PyPI. We rename by patching `pyproject.toml` during the build:

```bash
sed -i 's/^name = "python-gammu"/name = "python-gammu-ha"/' pyproject.toml
```

The import name (`import gammu`) stays the same — only the distribution metadata changes.

## Artifacts Produced

- **GitHub Actions workflow:** `.github/workflows/build-gammu-wheels.yml` (committed, on main)
- **GitHub Release:** `gammu-wheels-3.2.6-cp314` (pre-release)
  - `python_gammu-3.2.6-cp314-cp314-musllinux_1_2_x86_64.whl` (1.84 MiB)
  - `python_gammu-3.2.6-cp314-cp314-musllinux_1_2_aarch64.whl` (1.84 MiB)
- **Local validation:** Tested successfully on real HA instance with manually edited manifest

## Workflow (not pushed — PyPI variant)

The workflow was extended (locally, not committed) to:

- Rename `python-gammu` → `python-gammu-ha` in `pyproject.toml` during build
- Add `publish-pypi` job using `pypa/gh-action-pypi-publish` with OIDC Trusted Publisher
- Add `publish_pypi` boolean input to allow build-only runs
- Validate that `importlib.metadata.version("python-gammu-ha")` works in clean container

PyPI setup would require:

1. Create "Pending Publisher" on PyPI for `python-gammu-ha` pointing to this repo/workflow
2. Create GitHub Environment named `pypi`
3. No API token needed — uses OIDC

The `manifest.json` change would be: `"requirements": ["python-gammu-ha==3.2.6"]`

## Why We Shelved This

### Ongoing maintenance burden

| Trigger                                           | Frequency           | Risk                                                                       |
| ------------------------------------------------- | ------------------- | -------------------------------------------------------------------------- |
| HA bumps CPython (e.g., 3.14 → 3.15)              | ~Annually           | Low effort if build succeeds; high effort if new compiler/ABI issues arise |
| GCC introduces new warnings-as-errors             | Unpredictable       | Requires patching C code you don't own                                     |
| python-gammu upstream breaks or goes unmaintained | Could happen        | You become de-facto maintainer of a C extension                            |
| gammu C library becomes incompatible              | Low probability     | Source is on GitHub but project has minimal activity                       |
| Bad wheel published to PyPI                       | Your responsibility | Breaks every HACS user's HA instance on next restart                       |

### The HA core team reached the same conclusion

They removed the integration specifically because they didn't want to maintain the C library build pipeline. We validated that it's technically feasible, but the maintenance posture is the same reason they walked away.

### Add-ons already work

The GSM SMS Gateway Enhanced add-on bundles everything in Docker, has zero dependency on HA's Python packaging, and works today. The audience that _needs_ HACS (HA Container / HA Core users without Supervisor) is small and shrinking.

## How to Revive This

If the decision is revisited, the steps are:

1. Update the workflow with the PyPI rename + publish changes (documented above)
2. Set up PyPI Trusted Publisher for `python-gammu-ha`
3. Create GitHub `pypi` environment
4. Run the workflow with `publish_pypi=true`
5. Update `manifest.json`: `"requirements": ["python-gammu-ha==3.2.6"]`, bump version
6. Roll back deprecation notices in README.md, info.md, CHANGELOG.md
7. Commit, push, release

All the hard technical problems are solved. The workflow is parameterized. It's a matter of deciding to take on the maintenance.
