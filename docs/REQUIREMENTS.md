# Requirements and evidence matrix

**Lab:** CSC418 DevOps lab mid, COMSATS Attock  
**Instructor:** Babar Shazad  
**Assessment:** 40 core marks + 10 optional bonus marks

## Status and scope

This matrix maps the exact requirements to the supplied implementation. Local verification is recorded in `LOCAL_VERIFICATION.md`; it does not replace the required GitHub demonstration.

- **Locally implemented:** server-side validation and SQLite API, frontend, real unittest reporting, receiver, sender, defect toggle, and workflow. Use the local verification record for observed execution results.
- **External configuration required:** GitHub repository secrets, an authenticated tunnel, and a continuously running receiver must be configured by the owner.
- **External proof — not performed on your behalf:** GitHub push runs, automatic CI-to-local report delivery, Pages publishing, and email receipt require your own evidence.
- **Documentation completed:** these guides explain the contract and supply blank GitHub evidence records. They complement, not replace, the application's README.

“Implemented” is not “demonstrated on GitHub”; “configured” is not “received/deployed.” Mark external requirements complete only after obtaining real evidence.

## 1. Mark allocation

| Category | Marks | Required outcome |
| --- | ---: | --- |
| Submission portal | 8 | Accept, validate, save, and list assignment submission links |
| GitHub repository | 4 | App, tests, CI configuration, receiver, and README |
| Tests on every push | 10 | Real automated cases; test failure fails the stage |
| Local JSON receiver | 14 | Automatically receives actual passing and failing reports with required metadata/results |
| Demonstration | 4 | Passing push, broken push, repaired push, and JSON update evidence |
| **Core total** | **40** | All core requirements |
| Optional static Pages deployment | 5 | Successful same-revision checks, `main` only; failed revision does not replace prior version |
| Optional email notifications | 5 | Actual pass and fail emails to configurable recipient using SMTP secrets |
| **Bonus total** | **10** | Optional; do not claim without proof |
| **Maximum** | **50** | 40 core + 10 bonus |

## 2. Core coverage matrix

Marks belong to the categories above; rows below are checks, not extra marks.

| Requirement | Local implementation | External setup | Evidence required — not yet recorded |
| --- | --- | --- | --- |
| Four portal inputs | Static form accepts name, registration number, assignment title, submission URL | None beyond running the local server | Form screenshot and real valid test |
| No file upload | Store the submission link, not an uploaded file | None | UI/code inspection |
| Validate all required fields | Server rejects incomplete input with useful feedback | None | Missing-registration case executes; rejection message visible |
| Validate URL | Server rejects clearly invalid URL input | None | Invalid-URL test, including no-save assertion |
| Save and list | `server.py` persists accepted submissions in `data/submissions.db`; frontend shows stored list | Local server available at `http://127.0.0.1:8000` | Valid case proves accepted, persisted, and listed |
| GitHub repo contents | App, tests, CI workflow, receiver, README | Initialize/push repository and supply setup instructions | Repository URL and file-tree evidence |
| Every push runs actual tests | Workflow invokes `python3 scripts/run_tests.py`; suite uses `unittest` | Registered runner with Python 3.10+; workflow enabled on push for all branches | Actual GitHub run links and test logs |
| Required case 1 | Valid submission saved and listed | None beyond runner setup | Actual test name, result, and persistence/list assertions |
| Required case 2 | Missing registration rejected with message and not saved | None beyond runner setup | Actual test name/result and useful rejection message |
| Required case 3 | Invalid URL rejected and not saved | None beyond runner setup | Actual test name/result and no-save assertion |
| Failure is genuine | Runner writes actual `test-report.json`; nonzero exit on failure/error; no ignored test failure | Workflow preserves exit status | Broken run test step/job is failed |
| Receiver endpoints | `receiver.py`: `GET /health`, authenticated `POST /report`, port 9000 | Keep receiver alive outside the runner workspace | Health observation plus actual report delivery; health alone is insufficient |
| Receiver authentication | Required `REPORT_TOKEN`; sender header `X-Report-Token` | Secret `LOCAL_REPORT_TOKEN` matches receiver token and maps to sender `REPORT_TOKEN` | Successful authorized automated delivery without revealing token |
| Automatic pass and fail delivery | `scripts/send_report.py` posts generated report; sender uses `always()` after tests | Reachable receiver; runner and receiver on same machine | Sender step succeeds on both pass and fail; received reports match runs |
| Required report contents | Actual metadata, test outcomes, failure messages, counts, overall status | GitHub run context available to report generation/sending | Inspect actual received JSON using the content checklist below |
| Safe report persistence | Receiver atomically saves latest `test-report.json` in startup cwd by default | Start in `$HOME/labmid-reports`, not checkout | Receiver updates intact file; preserve copies for all three runs |
| Independent artifact evidence | Actual report upload uses `always()` | Artifact upload configured in workflow | Artifact from passing and failing runs; it does not replace receiver proof |
| Pass/break/fix demo | `scripts/demo_defect.py introduce` disables URL validation; `fix` restores it | Three commits pushed, runner/receiver continuously available | Three run identities, statuses, actual received JSON updates and screenshots |

## 3. Required JSON content checklist

The report uses schema version 1. Top-level metadata keys are `repository`, `branch`, `commit_sha`, `run_id`, and `timestamp`; outcomes are in `tests` and counts/status in `summary`. Each test has `name`, `result`, and `failure_message`. Verify all required contents against the actual GitHub run.

| Required content | How to verify |
| --- | --- |
| Repository | Matches submitted repository |
| Branch | Matches branch of the demonstrated push |
| Commit SHA | Matches the full tested revision |
| Run ID | Matches the GitHub Actions run |
| UTC timestamp | Actual report/run timestamp explicitly represented in UTC |
| Test names and results | Actual executed cases, not hard-coded predictions |
| Failure messages | Real assertion/error information for unsuccessful cases |
| Total, passed, failed | Actual counts consistent with the runner's outcome representation |
| Overall status | Reflects actual test success/failure, not sender success alone |

Errors have `result: "error"` and are included in `summary.failed`. Skips have `result: "skipped"` and are counted in `summary.skipped`, not as passes. The count formula is `total = passed + failed + skipped`. Failures/errors and zero discovered cases fail the run. A suite with skips can still have a passed overall status, so verify that each required case actually executed and passed. Local metadata may be `null` when unavailable; GitHub evidence must contain its real identity.

## 4. Optional bonus coverage

| Bonus | Local implementation | External configuration required | External proof — not performed |
| --- | --- | --- | --- |
| Pages: 5 marks | Static frontend deployment is gated on `main` and a successful tests/report job for the same SHA; failed revision leaves previous version unchanged. Static demo uses clearly labelled browser `localStorage`, not SQLite. | Explicit opt-in repository variable `ENABLE_PAGES=true`; eligible GitHub plan/repository, Pages configuration and required deployment permissions | Pages URL, passing deployed revision, skipped/blocked broken deployment, unchanged previous version, and fixed deployed revision |
| Email: 5 marks | Notify on both passing and failing test outcomes; configurable recipient; notification must not hide test failure | Secrets `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TO`; provider-compatible SMTP/TLS settings | Actually received pass and fail emails tied to run/SHA, with secrets redacted |

### Pages plan and security boundary

The core workflow uses GitHub-hosted runners. The local receiver remains protected by its
token and is reached through the configured tunnel URL. GitHub Pages for a private repository
may not be available on a free plan. Leave `ENABLE_PAGES` unset/false if not attempting Pages.

Pages serves static files only. It cannot run the local HTTP server or host `data/submissions.db`. The browser-local demo must be visibly distinguished from the shared local server workflow. Passing backend tests are not a claim that every behavior of this separate static mode was tested.

For SMTP, normally use port 587 with STARTTLS or port 465 with implicit TLS, as supported by the provider. `SMTP_TO` supplies the configurable recipient. Secret configuration without actual email receipt is incomplete bonus evidence.

## 5. Chosen project contract and operational checks

| Contract item | Required setting/check |
| --- | --- |
| Runtime | Python 3.10+ and standard library only; no external packages |
| Web server | `python3 server.py`, `http://127.0.0.1:8000` |
| Frontend files | `static/index.html`, `static/app.js`, `static/styles.css` |
| Database | `data/submissions.db` |
| Test command | `python3 scripts/run_tests.py`; default report is `<project root>/test-report.json` regardless of cwd; `--output` overrides it |
| Shared helpers | `validation.py`, `http_support.py`, `reporting.py` |
| Sender command | `REPORT_TOKEN` in environment, then `python3 scripts/send_report.py`; default report is project-root `test-report.json`; use `--report` to match a custom test output |
| Sender destination | `REPORT_RECEIVER_URL` defaults to `http://127.0.0.1:9000/report` |
| Receiver command | Set required `REPORT_TOKEN`; start `python3 receiver.py` through its absolute path from the separate reports directory |
| Default received report | `$HOME/labmid-reports/test-report.json` when started there |
| Runner | GitHub-hosted Ubuntu runner with Python configured by `actions/setup-python` |
| Trigger and trust | Every push; private trusted repository; no forks/untrusted contributors; no `pull_request` trigger |
| Failure follow-up | Sender and report artifact use `always()`; test step still fails |
| Defect commands | `python3 scripts/demo_defect.py introduce` and `python3 scripts/demo_defect.py fix` |

Localhost on a GitHub-hosted runner refers to the remote runner, not the student's machine.
The secured tunnel and `REPORT_RECEIVER_URL` secret bridge that network boundary.

## 6. Submission and honest completion record

Required submission: repository URL, setup instructions, and evidence. Include Pages URL and email evidence only if attempting those bonuses.

| Item | Completion/evidence boundary |
| --- | --- |
| Documentation | Guides and blank GitHub evidence template provided |
| Local implementation | App, tests, receiver, scripts, and CI/bonus workflow supplied |
| Local execution evidence | See `LOCAL_VERIFICATION.md`; local-only results do not establish GitHub execution |
| GitHub repository/runner/secrets | Owner setup required |
| Passing, broken, fixed GitHub runs | Owner demonstration and run links required |
| Automatic CI-to-local receiver updates | Actual passing/failing GitHub delivery evidence required |
| Pages deployment and unchanged-version proof | Not performed on your behalf; optional |
| Received pass/fail emails | Not performed on your behalf; optional |

Fill the blank evidence record in `DEMO_CHECKLIST.md` from actual results. `EXPLAINED.md` explains setup and lifecycle; `VIVA_GUIDE.md` provides the short oral explanation and 25 focused answers. Do not replace an unperformed external proof with a sample JSON or a simulated run.
