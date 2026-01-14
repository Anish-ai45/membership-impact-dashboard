**Copilot Instructions**

This repository currently has no detectable source files or agent instruction documents (search performed 2026-01-10). Use this document as the canonical, minimal onboarding guide for AI coding agents working here.

**Current Repo State:**
- **Status:** No top-level language manifests or obvious source directories found. Check [README.md](README.md) for project intent.

**Immediate discovery steps (run first):**
- **List top-level files:** `ls -la` and open [README.md](README.md) if present.
- **Look for language manifests:** check these paths: [package.json](package.json), [pyproject.toml](pyproject.toml), [requirements.txt](requirements.txt), [go.mod](go.mod), [Cargo.toml](Cargo.toml).
- **Search code & tests:** look in `src/`, `app/`, `lib/`, `cmd/`, `pkg/`, `tests/`, `__tests__/`.
- **Check CI and infra:** inspect `.github/workflows/`, `Dockerfile`, and `docker-compose.yml`.

**If you find a Node.js project:**
- Install: `npm ci` or `pnpm install` depending on lockfile. Run tests: `npm test` or `pnpm test`.
- Source layout to expect: `src/` (TS/JS), `lib/` (build output), `package.json` scripts define build/test commands.

**If you find a Python project:**
- Use `python -m venv .venv && source .venv/bin/activate` then `pip install -r requirements.txt` or `pip install .` for `pyproject.toml` projects.
- Tests usually live under `tests/` and run with `pytest`.

**Patterns & conventions to look for (examples to cite):**
- Test discovery: `pytest` or `npm test` scripts — cite the test runner defined in the manifest.
- CI checks: `.github/workflows/*` typically reference exact commands; mirror those locally when possible.
- Docker usage: If `Dockerfile` exists, prefer reproducing containerized build steps to match dev environment.

**How to update this file (merge guidance):**
- If `.github/copilot-instructions.md` already exists, preserve any project-specific bullets and integrate missing discovery steps above.
- Keep this file concise (20–50 lines). Prioritize concrete commands and exact filenames.

**When uncertain, ask the maintainer:**
- Ask: "What is the primary language and the intended entrypoint (README or main file)?" and "Which commands should I run to build and test locally?"

If you'd like, I can re-run discovery after you add files or grant access to a snapshot of the source tree.
