# Works on My Codex

Works on My Codex (WOMC) is a Codex plugin for adding a thin, project-specific harness to an empty folder or an existing SaaS, web, or app project. It inspects the project first, preserves existing work, and creates or updates a managed section in the root `AGENTS.md` containing only durable project context, project-specific guardrails, and reusable completion checks.

The task and its one-off acceptance criteria stay in the conversation. WOMC leaves implementation choices to Codex and does not turn every request into permanent process documentation or force a framework or browser dependency.

WOMC also includes a default Codex status line matching the native footer order: model with reasoning effort, permission mode, weekly remaining, context remaining, and project folder. Codex inserts the permission mode automatically; WOMC selects the other four native items.

## Install

Add this GitHub repository as a Codex marketplace, then install the plugin:

```sh
codex plugin marketplace add yeejh96-bit/worksonmycodex --ref main
codex plugin add works-on-my-codex@works-on-my-codex
```

Those commands change the user's Codex plugin configuration. Review them and run them explicitly. On the first new Codex session, review and trust the WOMC `SessionStart` hook with `/hooks`; then start one more session so the status-line setting loaded by Codex includes the hook's update. The hook updates `tui.status_line` once, preserves unrelated settings, and records success in plugin data so later user customization is not overwritten.

For development without installing, invoke the bundled generator directly. The generator reads known manifests but does not interpret commands written in prose, so pass those commands explicitly:

```sh
python3 skills/works-on-my-codex/scripts/setup_harness.py \
  --project /path/to/project \
  --check-command "make test" \
  --dry-run
python3 skills/works-on-my-codex/scripts/setup_harness.py \
  --project /path/to/project \
  --check-command "make test"
```

## Use

Ask Codex: `Use $works-on-my-codex to set up WOMC in this project.` Add the product purpose, durable guardrails, or reusable project completion checks if they are known. Keep the current task and its one-off acceptance criteria in the conversation. Codex inspects the repository, records exact safe validation commands from manifests, task runners, test configuration, and project documentation, previews and applies the managed block, reviews the diff, and runs those commands.

The trusted plugin hook configures the lower TUI status line once for all projects. To preview, repair, or apply it manually, ask: `Use $works-on-my-codex-statusline to configure the WOMC status line.` You can also make the same selection with `/statusline`.

Codex renders `weekly-limit` and `context-remaining` as percentages remaining. The permission mode, such as `Full Access`, is shown automatically and is not a selectable `tui.status_line` item. Codex omits the weekly item when that account window is unavailable.

Empty-project example:

```text
Use $works-on-my-codex here. This will be a personal expense web app. Keep it local-only for now. Done means the main flow works in a browser.
```

Existing-project example:

```text
Use $works-on-my-codex in this repository. Preserve our AGENTS.md and current changes. Use the existing lint, typecheck, test, build, and browser tooling.
```

## Files and behavior

- Creates `AGENTS.md` when no active root instruction file exists.
- If a non-empty root `AGENTS.override.md` exists, updates its managed block because Codex gives it precedence over `AGENTS.md`.
- Preserves user-authored instruction text and owns only the `womc:project-harness` marked block on later runs.
- Refuses to write when WOMC markers are partial or duplicated.
- Keeps the current task, generic agent behavior, and one-off acceptance criteria out of the generated block.
- Does not create nested `AGENTS.md` or product documents unless the repository genuinely needs scoped rules or longer durable context.
- Does not create Codex apps, MCP servers, custom status-line executables, or project permission configuration.
- Includes a trusted, one-time `SessionStart` hook that applies only the documented native status-line selection. Codex requires the user to review and trust plugin hooks before they run.

WOMC requires explicit approval before reading or exposing secrets, deleting data, changing a production database, making a real payment, deploying, changing an external service, or changing a remote repository. Normal project edits and local lint, typecheck, tests, builds, and dev-server runs remain autonomous and reversible.

## Remove

Remove only the complete WOMC marked block from the target project's active root `AGENTS.md` or `AGENTS.override.md`; keep all surrounding user content. Delete that file only if it contains nothing else and you intend to remove it. To uninstall the plugin, run `codex plugin remove works-on-my-codex@works-on-my-codex` after reviewing that command's scope.

## Limits

Detection is intentionally conservative. Custom task runners, commands hidden in prose, required services, credentials, and visual expectations may need project-specific input. A detected command is still run and judged by Codex after setup; its presence is not treated as proof that it passes. Browser verification depends on the project's existing server/tooling and the current environment's browser access.

When invoking the generator directly, repeat `--check-command` for exact validation commands that conservative detection cannot discover:

```sh
python3 skills/works-on-my-codex/scripts/setup_harness.py \
  --project /path/to/project \
  --check-command "make test" \
  --check-command "make build"
```

The legacy `reference/womc` material is development reference only, not a runtime dependency. The shipped manifest, skill, and generator work independently when the reference tree is absent.

## Verify this repository

```sh
python3 -m unittest discover -s tests -v
WOMC_RUN_CODEX_INTEGRATION=1 python3 -m unittest tests.test_codex_integration -v
python3 /home/lee/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/works-on-my-codex
python3 /home/lee/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
```

The integration test launches one read-only, ephemeral Codex turn and therefore uses the configured account and network. It is skipped unless explicitly enabled. The last two absolute paths are development-machine examples; use the corresponding validator paths in your Codex installation.
