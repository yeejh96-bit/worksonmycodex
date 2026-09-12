---
name: works-on-my-codex
description: Set up or refresh a thin Codex project harness in a blank or existing software project. Use when a user asks to apply Works on My Codex, WOMC, create project AGENTS.md guidance, or connect project rules and completion criteria to real validation commands. Do not use for ordinary feature implementation when harness setup was not requested.
---

# Works on My Codex

Create a short, project-specific Codex harness. The user supplies the changing task in chat; do not persist a task backlog in the harness.

## Inspect before writing

Resolve the requested project root, then inspect its directory layout, manifests, lockfiles, README and contributor docs, existing `AGENTS.md` files, test configuration, runnable scripts, and `git status`. Do not open secret-bearing files such as `.env`, credential stores, or private keys. Distinguish an empty project from an existing one and preserve uncommitted work.

Use the bundled `scripts/setup_harness.py` for the active root instruction file's managed block. Run it first with `--dry-run`. Add `--purpose`, `--guardrail`, or `--done` only for stable project facts the user provided. Add each exact safe local validation command established by a manifest, task runner, test configuration, project document, or the user with a separate `--check-command`. Prefer an explicit project command over guessing from a directory name. Resolve the script path relative to this `SKILL.md`; do not assume the target project contains the plugin. The generator updates a non-empty root `AGENTS.override.md` when present because Codex gives it precedence over `AGENTS.md`.

Review the proposed block against the inspected project. Confirm that its commands cover the repository's real completion path, including scoped commands for affected workspaces when necessary, then run the same command without `--dry-run`. If the script reports a marker conflict, stop and explain it; never repair ambiguous markers by deleting content. Review the resulting diff before continuing.

## Keep the harness thin

- Treat the current task as chat input, not permanent project configuration.
- Put only project-wide, durable constraints and command-backed completion criteria in the root `AGENTS.md`.
- Keep existing user-authored `AGENTS.md` content. WOMC owns only the marked block.
- Add a nested `AGENTS.md` only when a large repository has a subtree whose real commands or constraints differ from the root. Inspect the applicable instruction chain before doing so.
- Create a separate product or requirements document only when durable product context is too detailed for a short link from `AGENTS.md`. Preserve an existing documentation convention.
- Do not encode generic development advice, speculative future needs, or an implementation sequence Codex can decide per task.

## Validate the setup

Run each safe local command recorded in the generated block when its toolchain and dependencies are available. Report the exact command and result. If a command cannot run, report the concrete missing executable, dependency, service, fixture, or configuration; do not describe an unrun command as passing.

Do not claim that Codex loaded the harness merely because the file exists. If the user requests a live discovery check, run a read-only, ephemeral `codex exec` from the target root and confirm that it reports the intended project instructions. During plugin development, use the opt-in integration test documented in this plugin's README; it creates an isolated project and checks a unique harmless token. Do not consume an account or network resource for either check without authorization.

For a web project, prefer its existing dev server and browser/E2E tooling. Verify the changed user flow and relevant visual states in a browser when the environment provides browser access. Do not install Playwright, a framework, or another dependency merely to standardize the harness; propose or add a dependency only when the task clearly needs it.

Use independent verification only for authentication, payments, database or deployment changes, security/privacy work, or a large change surface. Give the verifier the diff, completion criteria, and raw command results, and require an independent inspection rather than acceptance of the implementer's summary. Ordinary harness setup does not require a second agent.

Finish by listing created or updated files, preserved conflicts or limitations, and validation results. Do not commit, push, deploy, or change external services unless the user requested and authorized the specific action.
