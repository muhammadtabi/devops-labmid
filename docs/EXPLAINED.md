# Explained lab guide: Assignment Submission Portal

**Course:** CSC418 DevOps lab mid, COMSATS Attock  
**Instructor:** Babar Shazad  
**Marks:** 40 core + 10 optional bonus

## 1. What this project does

A student enters their name, registration number, assignment title, and submission URL. The portal checks the input, saves an accepted submission, and displays the submissions list. It stores a link to the assignment; it does **not** upload files.

The main lesson is automation: a GitHub push runs real tests, sends the actual results to a local JSON receiver, and leaves evidence of both success and failure.

### Verification status

GitHub pushes, Pages deployment, and email receipt require your own repository/account setup and actual evidence. Local verification is recorded separately in `LOCAL_VERIFICATION.md`; it is not proof of a GitHub run. Fill `DEMO_CHECKLIST.md` from your own pass/break/fix pushes.

In the commands below, replace `/absolute/path/assignment-portal` with the actual project directory. `$HOME/labmid-reports` is a separate reports directory outside both the project and runner checkout.

## 2. Keep the technology simple

| Part | Contract |
| --- | --- |
| Runtime | Python 3.10 or newer, standard library only; no third-party dependencies |
| Local web server | `server.py`, at `http://127.0.0.1:8000` |
| Shared helpers | `validation.py` checks submissions; `http_support.py` handles JSON HTTP; `reporting.py` checks and atomically writes reports |
| Local frontend | `static/index.html`, `static/app.js`, `static/styles.css` |
| Local storage | SQLite, at `data/submissions.db` |
| Tests | Python `unittest`, launched by `python3 scripts/run_tests.py` |
| Test output | Actual `test-report.json`; a failed test makes the command exit unsuccessfully |
| Local report receiver | `receiver.py`, port 9000, `POST /report`, `GET /health` |
| Report sender | `python3 scripts/send_report.py` |
| CI machine | Local self-hosted GitHub Actions runner, named and labelled `labmid`, with `python3` installed |
| Optional Pages demo | Static frontend using browser `localStorage`, not the Python/SQLite backend |

There is no need for Docker, Jenkins, Terraform, or a package installation step. The main portal uses SQLite. The optional Pages demo has a different, clearly labelled browser-local storage mode.

## 3. Request lifecycle: form to saved list

1. The browser loads the static frontend from the local Python server.
2. The student fills in the four fields and submits the form.
3. The frontend sends the entered values to the server.
4. The server checks **all required fields** and validates the submission URL. Browser checks alone are not enough: a client can bypass them.
5. If input is invalid, the server returns a useful rejection message and does not save a row.
6. If input is valid, the server inserts the submission into SQLite.
7. The frontend displays the accepted submission in the list, using the server's stored data.

The API uses `POST /api/submissions` to submit and `GET /api/submissions` to list. A saved submission returns HTTP 201; validation rejection returns HTTP 400 with a general `error` and field-level `errors`. The list response has a `submissions` array. Input fields are `name`, `registration_number`, `assignment_title`, and `submission_url`. URL validation permits valid HTTP/HTTPS URLs with a host and without embedded credentials; it does not fetch the linked assignment. Use a normal `https://` URL for the successful case and `not-a-url` for the invalid case.

## 4. The three required automated cases

Run the real suite with:

```bash
cd /absolute/path/assignment-portal
python3 scripts/run_tests.py
```

| Case | Input | Required assertion |
| --- | --- | --- |
| Valid submission is saved and listed | Name, registration number, assignment title, valid submission URL | Submission is accepted, persisted, and returned in the list |
| Missing registration number is rejected | All other values valid; registration number empty or absent | Request is rejected with a useful message; no submission is saved |
| Invalid URL is rejected and not saved | All required values supplied; URL such as `not-a-url` | Request is rejected; storage/list does not gain that submission |

Tests should exercise the real application behavior, not just print expected answers. Use isolated temporary test storage so tests do not change a student's real submissions. Read the actual test names from the generated report rather than assuming names from this table.

### What makes a test run honest?

- The test runner records the outcomes produced by `unittest`.
- It creates `test-report.json` even when an assertion fails.
- It exits with a nonzero status when a test fails or errors. The CI test step must therefore fail.
- The workflow must not use `continue-on-error`, `|| true`, or another workaround to turn a failing test step green.
- A report is evidence of a run, not a hand-written prediction of the result.

A skipped test is not a pass. A test error is not a pass either. The report stores each error as `result: "error"`, includes it in `summary.failed`, and counts skips separately as `summary.skipped`. Thus `summary.total = summary.passed + summary.failed + summary.skipped`. Errors/failures make the overall run unsuccessful, and zero discovered tests also fail. A suite containing skips can still have a passed overall status, so explicitly check that all three required cases executed and passed.

The runner's default output is `<project root>/test-report.json`, independent of the terminal's current directory. `--output` selects another path. If changing it, also tell the sender the same path with `--report`; the default sender reads the project-root report. This is different from the receiver, whose default output uses its startup working directory.

## 5. Start the local components

Complete repository initialization and the GitHub setup instructions in the project README first. These docs do not create or replace that README.

### Terminal A: local portal

```bash
cd /absolute/path/assignment-portal
python3 server.py
```

Open `http://127.0.0.1:8000`. Try the form and list. No file-upload control is required.

### Terminal B: receiver outside the runner workspace

**Do not start the receiver from inside the repository or the runner checkout.** GitHub checkout cleanup can remove untracked files there, including the instructor's report. The receiver saves its default report in its startup working directory.

```bash
mkdir -p "$HOME/labmid-reports"
cd "$HOME/labmid-reports"
read -r -s -p "Receiver token: " REPORT_TOKEN
printf '\n'
export REPORT_TOKEN
python3 /absolute/path/assignment-portal/receiver.py
```

Enter your own strong token at the prompt. The prompt avoids putting the token directly into the command history. `REPORT_TOKEN` is required. Never commit the token or include it in screenshots.

The expected saved file is:

```text
$HOME/labmid-reports/test-report.json
```

The receiver should replace that file atomically: write a complete new file, then replace the old one. A reader should not see a half-written report. The file is the latest report, not necessarily a history of all runs; save separate evidence copies after each demo push.

Check `http://127.0.0.1:9000/health`. A healthy receiver only proves that the service is up; it does not prove a report was delivered.

### Terminal C: self-hosted runner

Follow GitHub's repository runner registration instructions from the README. Name the runner `labmid` and add the custom label `labmid`. A display name alone does not select a runner; the workflow must target its labels, including `self-hosted` and `labmid`.

Run it on the **same machine** as the receiver, with Python 3.10+ available as `python3`. Keep both the runner and receiver running for all three demo pushes.

Use only a private, trusted repository. Do not allow forks or untrusted contributors to execute code on this runner. The required workflow triggers on **every push**, not `pull_request`.

## 6. Why localhost needs the right runner

`127.0.0.1` means “this machine.” For a GitHub-hosted runner, it means GitHub's machine, not your laptop. That runner cannot reach your local receiver through your laptop's loopback address.

The chosen solution is a local self-hosted runner on the receiver's machine. Its sender can reach `http://127.0.0.1:9000/report` directly. No container is used, so there is no separate container loopback address to handle.

A tunnel is an alternative if a remote runner is used, but it needs external configuration and authentication. It is not necessary for this project. If used, configure `REPORT_RECEIVER_URL` to the reachable `/report` address; never expose an unauthenticated receiver.

## 7. How actual results reach the receiver

The sender contract is:

```bash
python3 scripts/send_report.py
```

- Environment variable `REPORT_TOKEN` supplies the authentication token.
- `REPORT_RECEIVER_URL` defaults to `http://127.0.0.1:9000/report`.
- The sender submits the actual generated report with HTTP `POST /report`.
- Authentication uses the header `X-Report-Token`.
- The receiver saves the submitted report as `test-report.json` in its startup directory by default.

For a local sender check, first generate a real report, then enter the same token in that terminal:

```bash
cd /absolute/path/assignment-portal
python3 scripts/run_tests.py
read -r -s -p "Report token: " REPORT_TOKEN
printf '\n'
export REPORT_TOKEN
python3 scripts/send_report.py
```

A manual sender check is useful for setup, but it does **not** replace the requirement to send automatically from GitHub on both passing and failing pushes. Locally generated metadata may also differ from GitHub metadata.

The delivered CI report must contain:

- Repository, branch, commit SHA, and GitHub run ID.
- A UTC timestamp.
- Actual test names and their results.
- Failure messages for failing cases.
- Total, passed, and failed counts, plus overall status.

### Actual report schema, with a teaching-only example

Top-level keys are `schema_version`, `repository`, `branch`, `commit_sha`, `run_id`, `timestamp`, `tests`, and `summary`. Each test has `name`, `result`, and `failure_message`; summary has `total`, `passed`, `failed`, `skipped`, and `status`.

**The example below illustrates structure only. It is not generated evidence, a completed test run, or a GitHub result.** The illustrative name, message, and timestamp must never be submitted as proof. Metadata can be `null` for an ordinary local run when unavailable; actual GitHub evidence must identify its real repository, branch, SHA, and run ID.

```json
{
  "schema_version": 1,
  "repository": null,
  "branch": null,
  "commit_sha": null,
  "run_id": null,
  "timestamp": "2026-01-01T00:00:00Z",
  "tests": [
    {
      "name": "illustration.invalid_url_case",
      "result": "failed",
      "failure_message": "Illustration only: invalid input was accepted instead of rejected."
    }
  ],
  "summary": {
    "total": 1,
    "passed": 0,
    "failed": 1,
    "skipped": 0,
    "status": "failed"
  }
}
```

In real reports, passing tests have an empty `failure_message`; errors/failures carry the actual message. Compare the received SHA and run ID with the corresponding GitHub run, so an old file is not mistaken for new evidence.

## 8. CI lifecycle: push to outcome

Configure the repository secret **`LOCAL_REPORT_TOKEN`** to the same value entered for the receiver. The workflow maps it to `REPORT_TOKEN` for the sender.

For every push, the workflow must:

1. Select the trusted local self-hosted runner and check out that push's revision.
2. Run `python3 scripts/run_tests.py` using the installed Python.
3. Preserve the test command's exit status: failure means a failed test step/job.
4. Run the report sender with `always()` after the test step, so a failed test does not skip delivery.
5. Upload the actual test report as an artifact with `always()` as well, so delivery failure does not erase test evidence.

`always()` means the follow-up step is attempted even after a previous failure; it does not turn the failed test green. It cannot guarantee delivery if the runner is offline, the job is cancelled, or no report was produced. A missing report or unsuccessful delivery must be visible, not replaced with a fabricated passing report.

For the bonus deployment, the tests/report job must be successful. A successful test run with failed report delivery is not a successful tests/report job and must not unlock deployment. Artifact failure or an enabled email step failure also blocks Pages in the supplied workflow. The workflow additionally permits manual `workflow_dispatch` runs, but Pages is limited to eligible pushes; the required demonstration uses actual pushes.

## 9. Pass, break, fix demonstration

The actual defect command is:

```bash
python3 scripts/demo_defect.py introduce
```

It changes only `validation.py` to disable URL validation. The unchanged invalid-URL test should then detect that invalid input was accepted or saved. Push the changed validation module and show the resulting failed GitHub run and newly delivered failure report.

Restore the validation with:

```bash
python3 scripts/demo_defect.py fix
```

Commit and push the repair. Show the newly passing run and new receiver report. The defect must be in application behavior, not a fake report edit or deliberately wrong test expectation. Use `DEMO_CHECKLIST.md` for the exact commands and evidence sequence.

## 10. Optional bonuses

### Static GitHub Pages deployment: 5 marks

Pages is **opt-in**: set the repository variable `ENABLE_PAGES=true` only if attempting this bonus. Leave it unset/false for core-only work, so Pages availability cannot block core tests/report delivery.

A private repository on a free GitHub plan may not support Pages. Keep the core repository private and trusted; use an eligible plan or skip this bonus rather than exposing a self-hosted runner to untrusted public code.

Deploy only from `main`, and only after the tests/report job for the **same revision** succeeds. Do not deploy on a feature branch or after failed tests/report delivery. A failed revision must leave the previously published version unchanged.

GitHub Pages serves static files; it does not run `server.py`, accept backend requests, or host SQLite. The Pages version uses `localStorage` and must clearly say that submissions are stored only in that browser. Its data is separate from the local SQLite portal, not shared between users, and may disappear when browser storage is cleared.

Show the passing deployed version, confirm that the broken push did not replace it, and show the fixed deployment. Do not claim that backend tests fully test the separate Pages storage mode.

### Email notifications: 5 marks

If attempting email, configure secrets:

| Secret | Purpose |
| --- | --- |
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | Provider's supported port: normally 587 for STARTTLS or 465 for implicit TLS |
| `SMTP_USERNAME` | SMTP account username |
| `SMTP_PASSWORD` | SMTP password or provider-required app password |
| `SMTP_FROM` | Sender address allowed by the provider |
| `SMTP_TO` | Configurable recipient address |

Match the provider's TLS mode to its port. The email step is skipped when SMTP configuration is absent, so core work does not require email credentials. When configured, it sends notifications for both passing and failing test outcomes and reports delivery errors visibly. It must not be skipped just because tests failed, and must not hide that failure. Prove receipt of both messages, identifying the relevant run/SHA, without showing secrets. A configured secret is not proof that an email was sent or received.

## 11. What to submit

Submit the repository URL, setup instructions, and real evidence for the core requirements. The repository must contain the app, tests, CI configuration, receiver, and README. Add the Pages URL and pass/fail email evidence only if attempting those bonuses.

Do not state that GitHub, Pages, or email has been demonstrated until it actually has. Use the coverage matrix in `REQUIREMENTS.md` and complete the blank evidence record in `DEMO_CHECKLIST.md`.
