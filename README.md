# Prelaunch Test Audit Skill

`prelaunch-test-audit` is a reusable Codex skill for release-readiness testing, prelaunch audits, regression planning, security review, and Go/No-Go launch decisions.

It is designed to help an agent focus on launch risk that matters: money, permissions, data, availability, security, rollback, observability, and third-party integrations.

## Install

Clone this repository, then copy the skill directory into your Codex skills folder:

```powershell
Copy-Item -Recurse .\prelaunch-test-audit "$env:USERPROFILE\.agents\skills\prelaunch-test-audit"
```

On macOS or Linux:

```bash
cp -R prelaunch-test-audit ~/.agents/skills/prelaunch-test-audit
```

After copying, restart Codex or reload skills if your environment requires it.

## Use

Ask Codex:

```text
Use $prelaunch-test-audit in read-only audit mode to check whether this project is ready to launch.
```

Useful prompts:

```text
Use $prelaunch-test-audit to run a Go/No-Go launch review for this repo.
```

```text
Use $prelaunch-test-audit to identify high-risk routes, weak tests, missing rollback checks, and launch blockers.
```

```text
Use $prelaunch-test-audit to design regression tests for the payment, permission, and data-write flows.
```

## Included

```text
prelaunch-test-audit/
  SKILL.md
  agents/openai.yaml
  assets/templates/
  references/test-prompts.md
  scripts/prelaunch_static_scan.py
```

The `scripts/prelaunch_static_scan.py` scanner is read-only. It detects project manifests, package scripts, route inventory, security surfaces, weak-test patterns, lockfile gaps, potential secret-like values, and suggested safe commands.

## Examples

See:

- `examples/sample-audit-report.md`
- `examples/sample-go-no-go-report.md`
- `examples/sample-static-scan-output.md`

## Safety

The skill defaults to read-only audit behavior. Dynamic security testing should run against local or staging environments by default. Production checks should stay low-risk unless a user explicitly authorizes a specific scope.

