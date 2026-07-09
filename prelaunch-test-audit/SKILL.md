---
name: prelaunch-test-audit
description: Use when a project is preparing to launch, release, deploy, go live, or needs 涓婄嚎鍓嶆祴璇? 鍙戝竷鍓嶆鏌? 鍥炲綊娴嬭瘯, 鎺ュ彛瀹夊叏娴嬭瘯, release readiness review, production readiness, or a Go/No-Go launch decision.
---

# Prelaunch Test Audit

Version: 1.2.0

## Overview

Run a release-readiness audit that lowers real launch risk. Prioritize failures that can damage money, permissions, data, availability, or user trust.

Use this as an audit workflow first. Do not start fixing issues until the user confirms which findings to fix.

## Operating Rules

- Stay inside the user's authorized project, local environment, staging environment, or explicitly approved target.
- Do not run destructive, high-volume, or production-facing security tests without explicit approval.
- Default dynamic security testing to local or staging only. For production, perform only low-risk verification unless the user explicitly authorizes a specific test scope.
- Prefer reading code, existing tests, CI config, deployment config, migrations, logs, and docs before inventing checks.
- Report evidence: file paths, commands, requests, responses, failing tests, logs, or screenshots when available.
- Separate findings from fixes. First list risks and recommended fixes; modify code only after the user confirms.
- Make the final answer a launch decision: `Go`, `Conditional Go`, or `No Go`.

## Audit Modes

Default to `read-only audit` unless the user explicitly asks for test creation or fixes.

| Mode | Allowed | Not allowed |
|---|---|---|
| `read-only audit` | Inspect code, configs, tests, docs, logs, and safe command output | Edit code, change config, mutate data, run aggressive security tests |
| `test-authoring` | Add or improve automated tests for confirmed high-risk areas | Change production behavior except for test seams the user approves |
| `fix-after-confirmation` | Fix findings the user explicitly confirmed | Fix unrelated issues, silently expand scope, or skip re-running tests |

If the user asks "can we launch?" or "check before release", use `read-only audit`. If blockers are found, return findings and ask which ones to fix.

## Quick Start

1. Inspect the project shape:
   - README and setup docs
   - package/build/test scripts
   - backend routes, controllers, services, middleware
   - frontend critical flows
   - database schema, migrations, seed data
   - deployment files, environment examples, CI config
2. Optionally run the read-only scanner: `python scripts/prelaunch_static_scan.py <project-root>`.
3. Identify high-risk surfaces.
4. Design or run tests for those surfaces.
5. Validate that automated tests can fail for the right reason.
6. Review security, deployment, rollback, data migration, performance, observability, and third-party integrations.
7. Return a ranked findings list and Go/No-Go decision.

## Risk Triage

Rank features by consequence, not by how easy they are to test.

| Risk area | Examples | Priority |
|---|---|---|
| Money | payment, refund, pricing, discounts, credits, inventory deduction | Highest |
| Permissions | login, roles, ownership checks, admin APIs, password reset | Highest |
| Data | create/update/delete, imports, exports, migrations, user records, orders | Highest |
| Availability | slow queries, queues, uploads, rate limits, startup, health checks | High |
| Trust | notifications, email/SMS, privacy, audit logs, support workflows | High |
| Presentation | copy, color, minor layout, low-impact static pages | Lower |

If time is limited, go deeper on the highest-risk paths instead of spreading shallow tests across every screen.

## Severity Rules

Classify every finding with a severity. Do not leave high-risk findings unclassified.

| Severity | Meaning | Examples |
|---|---|---|
| `P0 Blocker` | Must not launch until fixed or explicitly accepted by the user with a rollback plan | money miscalculation, privilege escalation, data loss/corruption, leaked production secret, no viable rollback, production cannot start |
| `P1 High` | Serious launch risk that usually requires a fix or explicit conditional launch plan | core user journey broken, migration risk, payment/webhook failure, missing auth check on important endpoint, no monitoring for critical flow |
| `P2 Medium` | Important but bounded issue; can launch if owner accepts risk and follow-up is tracked | non-core flow bug, weak error handling, slow but tolerable endpoint, incomplete low-impact test coverage |
| `P3 Low` | Minor issue that should not block launch alone | copy, layout polish, low-impact edge case, internal cleanup |

When severity is uncertain, choose the higher severity and explain what evidence would lower it.

## Functional Testing

For each high-risk feature, cover three classes:

1. Normal path: the action succeeds and the business result is correct.
2. Boundary path: zero, negative, maximum, minimum, empty, duplicate, last-item, concurrent, expired, and repeated-submit cases.
3. Invalid path: unauthenticated calls, wrong user, wrong role, malformed input, extra fields, missing fields, and stale state.

Never accept "HTTP 200" or "success: true" as enough. Verify the resulting amount, ownership, status, row count, inventory, ledger entry, email, notification, or persisted data.

## Regression Test Net

Turn confirmed high-risk checks into automated tests that run with one command.

Always tell the user:

- the exact command
- what pass/fail looks like
- what key scenarios are covered
- which high-risk areas are still manual or untested

When adding tests, follow the repository's existing test framework. If there is no test framework, recommend the smallest suitable setup before adding one.

## Fake-Test Defense

Before trusting a new or existing test suite, prove tests can catch real faults:

1. Explain what business outcome each important test verifies.
2. Confirm the test exercises the real code path, with mocks only where unavoidable.
3. Temporarily introduce a deliberate fault in a safe local branch or working copy.
4. Run the relevant test and confirm it fails for the expected reason.
5. Revert the deliberate fault.

If a test still passes after the corresponding code is intentionally broken, mark it invalid and rewrite it.

## Security Audit

Use two passes:

1. Static review: inspect auth, authorization, validation, serialization, secrets, query construction, file handling, and rate limiting.
2. Dynamic check: when safe and authorized, send controlled requests against local or staging endpoints.

Dynamic checks default to local or staging environments. In production, limit activity to low-risk verification such as configuration review, health checks, existing logs/metrics, and explicitly approved read-only requests.

Check at least:

- horizontal access control: user A reading, changing, or deleting user B's data
- vertical access control: normal user calling admin-only APIs
- missing authentication and forged, expired, or tampered credentials
- mass assignment: extra submitted fields like `role`, `price`, `amount`, `isAdmin`, `ownerId`
- injection: SQL, command, script, path traversal, template, and unsafe deserialization
- frontend-only validation bypass
- sensitive response leakage: passwords, tokens, keys, internal errors, private phone/email data
- rate limit and abuse resistance on login, SMS/email, order, upload, AI, search, and export endpoints

Report reproduction details without dumping secrets or causing damage.

## Launch Engineering Checks

Do not stop at functional tests. Review the release system itself.

| Area | Check |
|---|---|
| Environment | required env vars, production/staging differences, HTTPS, CORS, cookies, callback URLs |
| Secrets | no committed secrets, rotated leaked keys, least-privilege credentials |
| Database | backups, migration order, rollback plan, idempotency, old data compatibility |
| Deployment | build artifacts, startup command, health check, static assets, cache invalidation |
| Rollback | previous version available, database rollback or forward-fix plan, owner assigned |
| Performance | slow endpoints, slow SQL, pagination, large exports, file upload limits, concurrency |
| Observability | structured logs, error tracking, alerts, trace IDs, audit logs for sensitive actions |
| Third parties | payment, SMS, email, OAuth, object storage, maps, AI APIs, webhook signatures and retries |
| Frontend | critical user journeys, mobile viewport, refresh/back behavior, duplicate clicks, error states |

## Supply Chain Checks

Inspect dependency and build-chain risk when the repository includes dependency manifests or containers.

- Check that lockfiles exist and match the package manager (`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `uv.lock`, `requirements.txt`, `Cargo.lock`, `go.sum`, etc.).
- Run the ecosystem's safe audit command when available and appropriate, such as `npm audit`, `pnpm audit`, `pip-audit`, `cargo audit`, `go list -m -u -json all`, or the repository's documented security scan.
- Review Dockerfiles, compose files, CI scripts, and build artifacts for embedded secrets, unsafe install steps, unpinned base images, or production debug settings.
- Treat critical or high dependency vulnerabilities in auth, crypto, request parsing, templating, upload, database, or admin surfaces as at least `P1 High`.
- If audit tools cannot run, report the exact reason and list the manifests that still need review.

## Go/No-Go Gate

Use these rules for the final decision:

- `No Go`: any unresolved `P0 Blocker`; production cannot build/start; migration or rollback is unsafe; confirmed data loss, money error, privilege escalation, or exposed production secret.
- `Conditional Go`: unresolved `P1 High` findings have an owner, mitigation, rollback path, and explicit user acceptance; some important checks could not be completed but risk is bounded and documented.
- `Go`: no unresolved `P0` or unaccepted `P1`; core tests pass; rollback, backups, environment, observability, and critical third-party paths are acceptable; remaining issues are `P2/P3` with follow-up.

Never return `Go` while hiding untested areas. A launch can be acceptable only if unknowns are named.

## Evidence Standard

Every `P0`, `P1`, and security finding must include:

- impact scope: which users, data, money, permissions, or systems are affected
- reproduction steps or review path
- actual result
- expected safe result
- evidence location: file path, line, command, request/response summary, log, screenshot, or test name
- recommended fix or mitigation
- launch impact: whether it blocks release

If evidence is incomplete, label the finding as "suspected" and explain what check would confirm or dismiss it.

## Output Format

Use `assets/templates/project_intake_template.md` to collect missing launch context, `assets/templates/audit_report_template.md` for full audit reports, `assets/templates/finding_template.md` for detailed findings, `assets/templates/test_case_template.md` for test design, `assets/templates/regression_report_template.md` for regression summaries, and `assets/templates/go_no_go_report_template.md` for final launch decisions.

If templates are unavailable, use this structure:

```markdown
## Launch Decision

Decision: Go | Conditional Go | No Go
Reason: ...
Gate rule applied: ...

## Blockers

| Severity | Area | Finding | Evidence | Recommended fix | Launch impact |
|---|---|---|---|---|---|

## High-Risk Findings

| Severity | Area | Finding | Evidence | Recommended fix | Launch impact |
|---|---|---|---|---|---|

## Tests Run

| Command | Result | Notes |
|---|---|---|

## Supply Chain Checks

| Check | Result | Notes |
|---|---|---|

## Coverage Notes

Covered:
Not covered:
Manual checks still needed:

## Fix Plan

Only include this as a proposal. Wait for user confirmation before editing code.
```

## Common Mistakes

- Testing every minor UI detail while missing payments, permissions, or data writes.
- Checking only status codes instead of persisted business results.
- Writing tests that only exercise mocks.
- Letting the audit silently edit code before the user reviews the findings.
- Running aggressive security checks against production.
- Forgetting rollback, backups, monitoring, and third-party callbacks.
- Calling something `Go` despite unresolved `P0`/unaccepted `P1` findings.
- Reporting vague concerns without reproduction steps, expected behavior, or launch impact.
- Claiming "ready to launch" without listing untested areas.

## Prompt Reference

If the user wants copy-paste Chinese prompts, or if you need to turn this workflow into user-facing instructions, read `references/test-prompts.md`.

## Bundled Resources

- `scripts/prelaunch_static_scan.py`: read-only repository triage. It detects manifests, package scripts, framework hints, route inventory, security surface hints, test candidates, weak-test patterns, config/deployment files, lockfile gaps, potential secret-like values, and suggested safe commands. It does not run tests, dependency audits, security probes, or mutate files.
- `assets/templates/project_intake_template.md`: launch context intake for details the code cannot reliably infer.
- `assets/templates/audit_report_template.md`: complete audit report layout.
- `assets/templates/finding_template.md`: per-finding evidence and launch-impact layout.
- `assets/templates/test_case_template.md`: business-outcome-first test case layout.
- `assets/templates/regression_report_template.md`: automated test result summary layout.
- `assets/templates/go_no_go_report_template.md`: final launch gate decision layout.
- `references/test-prompts.md`: Chinese copy-paste prompts for users who want to direct another agent manually.
