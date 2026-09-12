# Works on My Codex

Works on My Codex (WOMC) is a Codex plugin for adding a thin, project-specific harness to an empty folder or an existing SaaS, web, or app project. It inspects the project first, preserves existing work, and creates or updates a managed section in the root `AGENTS.md` that links an autonomous working contract, durable guardrails, and completion criteria to real project commands.

The task itself stays in the conversation. WOMC does not turn every request into permanent process documentation, force a framework or browser dependency, or require a separate verifier for routine work.

WOMC also includes an opt-in Codex status-line setup. It replaces the default thread name with the account's five-hour and weekly usage-limit indicators while retaining the model and current directory.

## Install

Codex 0.154.0 supports installation from a configured marketplace. Until this plugin is published in one, place this repository at `<marketplace-root>/plugins/works-on-my-codex` and create `<marketplace-root>/.agents/plugins/marketplace.json`:

```json
{
  "name": "works-on-my-codex-local",
  "interface": { "displayName": "Works on My Codex Local" },
  "plugins": [
    {
      "name": "works-on-my-codex",
      "source": { "source": "local", "path": "./plugins/works-on-my-codex" },
      "policy": { "installation": "AVAILABLE", "authentication": "ON_INSTALL" },
      "category": "Productivity"
    }
  ]
}
```

Then run:

```sh
codex plugin marketplace add <marketplace-root>
codex plugin add works-on-my-codex@<marketplace-name>
```

Those commands change the user's Codex plugin configuration. Review the marketplace path and run them explicitly; WOMC never edits global or personal Codex settings during project setup. Start a new Codex thread after installing so the skill is discovered.

For development without installing, invoke the bundled generator directly:

```sh
python3 skills/works-on-my-codex/scripts/setup_harness.py --project /path/to/project --dry-run
python3 skills/works-on-my-codex/scripts/setup_harness.py --project /path/to/project
```

## Use

Ask Codex: `Use $works-on-my-codex to set up WOMC in this project.` Add the product purpose, durable guardrails, or measurable completion criteria if they are known. Codex inspects the repository, records exact safe validation commands from manifests, task runners, test configuration, and project documentation, previews and applies the managed block, reviews the diff, and runs those commands.

To configure the lower TUI status line once for all projects, ask: `Use $works-on-my-codex-statusline to replace the thread name with five-hour and weekly limits.` Codex previews the change, preserves unrelated settings, and updates the user-level `config.toml` only after the request authorizes that global scope. Codex plugins cannot execute a post-install script, so installing alone does not alter personal settings. You can make the same selection manually with `/statusline`.

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
- Does not create nested `AGENTS.md` or product documents unless the repository genuinely needs scoped rules or longer durable context.
- Does not create Codex apps, MCP servers, hooks, custom status-line executables, or project permission configuration.
- Does not change the status line during installation. The separate status-line skill performs that personal configuration only when explicitly requested.

WOMC requires explicit approval before reading or exposing secrets, deleting data, changing a production database, making a real payment, deploying, changing an external service, or changing a remote repository. Normal project edits and local lint, typecheck, tests, builds, and dev-server runs remain autonomous and reversible.

## Remove

Remove only the complete WOMC marked block from the target project's active root `AGENTS.md` or `AGENTS.override.md`; keep all surrounding user content. Delete that file only if it contains nothing else and you intend to remove it. To uninstall the local example, run `codex plugin remove works-on-my-codex@works-on-my-codex-local` after reviewing that command's scope.

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
