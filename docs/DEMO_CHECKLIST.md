# Demo checklist: pass, break, fix

**CSC418 DevOps lab mid — COMSATS Attock — Babar Shazad**  
**Core:** 40 marks. **Optional bonuses:** 10 marks.

## Important: these are instructions, not completed evidence

All GitHub evidence fields below are deliberately blank. Fill them only from your actual runs. Local verification is recorded separately in `LOCAL_VERIFICATION.md`; a local test run, a sample JSON file, or this checklist is not proof of a GitHub run.

Replace `/absolute/path/assignment-portal` in commands with your extracted project directory. Use `$HOME/labmid-reports` outside both the project and runner checkout.

## 1. Before the demonstration

Complete repository initialization and GitHub settings **first**, following the project README. This document does not supply or replace that README. Do not run the demo commands until the application, test scripts, receiver, and workflow exist.

- [ ] Python 3.10+ is installed as `python3`; no third-party dependencies are needed.
- [ ] Repository contains the app, tests, CI workflow, receiver, and README.
- [ ] Git is initialized; your identity is configured; `origin` points to your GitHub repository; the local `main` branch exists.
- [ ] `REPORT_RECEIVER_URL` points to an authenticated tunnel or relay forwarding to the local receiver.
- [ ] Workflow triggers on every push and has no `pull_request` trigger.
- [ ] GitHub-hosted Ubuntu jobs can reach the tunnel; the receiver and tunnel remain running.
- [ ] GitHub secrets `LOCAL_REPORT_TOKEN` and `REPORT_RECEIVER_URL` are configured.
- [ ] Sender and artifact steps use `always()` after tests. Tests are not made green using `continue-on-error` or `|| true`.
- [ ] Secret values, `data/submissions.db`, and generated reports are excluded from commits as described in the README. Review the actual ignore configuration before staging.
- [ ] If attempting Pages, repository variable `ENABLE_PAGES=true` and Pages settings are configured; deployment requires `main` and successful same-revision tests/report delivery.
- [ ] If Pages is unavailable for a private repository on the current free plan, leave the bonus disabled. Use an eligible plan or skip it; do not make this self-hosted setup public to untrusted code. Core tests/report delivery must remain independent of Pages.
- [ ] Optional SMTP settings are configured only if attempting email.
- [ ] No unrelated work is mixed into the demonstration commits.

### Keep the receiver alive in its own directory

In a dedicated terminal:

```bash
mkdir -p "$HOME/labmid-reports"
cd "$HOME/labmid-reports"
read -r -s -p "Receiver token: " REPORT_TOKEN
printf '\n'
export REPORT_TOKEN
python3 /absolute/path/assignment-portal/receiver.py
```

Keep this terminal and the tunnel running through all three pushes. Check `http://127.0.0.1:9000/health`.

The default received file is `$HOME/labmid-reports/test-report.json`. Starting the receiver outside the checkout prevents GitHub checkout cleanup from deleting the instructor's record. Do not use the runner workspace as the receiver's storage directory.

For a UI demonstration, run `python3 server.py` from the project in another terminal and open `http://127.0.0.1:8000`.

## 2. Show the exact three required cases

Use both the test output and, where useful, the local UI:

1. **Valid saved/listed:** supply a name, registration number, assignment title, and valid submission URL. Verify it is saved and appears in the list.
2. **Missing registration:** keep other fields valid and omit the registration number. Show the rejection message and verify nothing new is saved.
3. **Invalid URL:** supply the required fields but use `not-a-url`. Show rejection and verify the invalid submission is not saved.

These are required behaviors, not assumed test function names. Use the real names in `test-report.json` when presenting results. A rejected input without a not-saved assertion is incomplete evidence for the invalid-URL case.

## 3. Push 1: passing baseline

Run these commands from the project. If the local tests fail, stop and repair the baseline before making this commit. Review the staged files so no secrets, live database, or generated reports are committed.

```bash
cd /absolute/path/assignment-portal
git switch main
git status --short
python3 scripts/run_tests.py
git add .
git diff --cached --stat
git diff --cached
git commit --allow-empty -m "demo: passing baseline"
git push -u origin main
git rev-parse HEAD
```

`--allow-empty` permits a baseline demo push even if the prepared implementation was already committed. Do not include unwanted staged files; correct staging before committing.

Wait for this exact GitHub run to finish before the next push:

- [ ] Test step passes, and the actual three required cases executed.
- [ ] Report sender runs automatically and succeeds.
- [ ] Actual report artifact is available.
- [ ] Receiver file now contains this repository, branch, commit SHA, run ID, UTC timestamp, test results, counts, and overall status.
- [ ] Failure messages are present when applicable; there are no unexplained skips or errors.
- [ ] GitHub and report identities match. A green run alone does not prove the receiver updated.

Only after confirming the received file matches this run, preserve a copy:

```bash
cp "$HOME/labmid-reports/test-report.json" "$HOME/labmid-reports/pass-$(git rev-parse HEAD).json"
```

If attempting Pages, wait for the successful deployment and record its URL and deployed revision before the broken push. If attempting email, retain the received passing notification.

## 4. Push 2: real broken validation

Start from the clean baseline. The defect script disables URL validation in the application. It does not fabricate a report or change tests to expect a failure.

```bash
cd /absolute/path/assignment-portal
python3 scripts/demo_defect.py introduce
git diff
python3 scripts/run_tests.py
```

**The local test command should exit nonzero now.** This is the expected failure. Inspect the real output before continuing. If it passes, stop: the invalid-URL test did not detect the defect, or the defect was not introduced. Do not substitute an edited JSON report.

After confirming the defect is in tracked application code, make the second commit and push:

```bash
git add validation.py
git diff --cached --stat
git diff --cached
git commit -m "demo: break URL validation"
git push origin main
git rev-parse HEAD
```

`git add validation.py` stages only the validation module changed by the defect script. Review the staged diff and ensure it contains only the intended defect, not unrelated changes or edits to generated evidence.

Wait for this exact run to finish:

- [ ] The invalid-URL case fails because invalid input was accepted or saved.
- [ ] GitHub test step/job is failed, not green with an ignored failure.
- [ ] The `always()` sender still runs automatically.
- [ ] The `always()` report artifact is still available.
- [ ] Receiver file is replaced with this broken revision's actual failed report.
- [ ] Report includes the actual failing test name and useful failure message.
- [ ] Report SHA and run ID match the broken run, not the baseline.

After verifying the received identity, preserve it:

```bash
cp "$HOME/labmid-reports/test-report.json" "$HOME/labmid-reports/fail-$(git rev-parse HEAD).json"
```

**Optional Pages:** show that no deployment from this failed revision occurred and the previously published version remains unchanged. A page merely loading is not enough; compare its published revision or a recorded observable version and deployment history. Do not expect the static Pages browser-local storage mode to reproduce a Python-backend-only defect.

**Optional email:** retain the actual received failing notification and match it to this run.

## 5. Push 3: fixed validation

Restore the real application validation. Do not change assertions to accept the defect.

```bash
cd /absolute/path/assignment-portal
python3 scripts/demo_defect.py fix
git diff
python3 scripts/run_tests.py
```

Continue only when the required cases execute and pass locally:

```bash
git add validation.py
git diff --cached --stat
git diff --cached
git commit -m "demo: restore URL validation"
git push origin main
git rev-parse HEAD
```

Wait for the new run:

- [ ] Test step passes again.
- [ ] Sender automatically delivers the actual new passing report.
- [ ] Report artifact is available.
- [ ] Receiver file has the fixed SHA/run ID and new UTC timestamp.
- [ ] All three required cases ran and passed; counts/status reflect the actual suite.

After confirming identity, preserve the final copy:

```bash
cp "$HOME/labmid-reports/test-report.json" "$HOME/labmid-reports/fix-$(git rev-parse HEAD).json"
```

If attempting Pages, verify the repaired revision is deployed only after its own tests/report job succeeds. If attempting email, verify the new passing notification.

## 6. Screenshot and file evidence

Capture real evidence without exposing tokens or SMTP passwords:

- [ ] Local form and saved submissions list; rejection messages for missing registration and invalid URL.
- [ ] Repository file tree showing app, tests, CI workflow, receiver, and README.
- [ ] Three GitHub run pages with branch, SHA, run ID, and status visible.
- [ ] Passing, broken, and fixed test outputs, including the real invalid-URL failure message.
- [ ] Sender and artifact step results on the failing run as well as passing runs.
- [ ] Three preserved receiver reports, tied to the corresponding GitHub identities.
- [ ] Optional Pages deployment history, URL, and proof the failed revision did not replace the published version.
- [ ] Optional actual received passing and failing emails with relevant run identities.

Take receiver evidence after each run. The receiver's latest-report file is overwritten, so waiting until the end loses earlier evidence unless copies were preserved. Report JSON must come from the automated sender; do not type expected values into it.

### Screenshot placeholders — no evidence attached yet

Replace each blank with the path or link to a real screenshot after capture. These are placeholders, not screenshot images or successful results.

| Screenshot | Actual file/link |
| --- | --- |
| Form, accepted submission, and saved list | ____________________ |
| Missing-registration message and invalid-URL rejection | ____________________ |
| Passing GitHub run and matching receiver report | ____________________ |
| Broken GitHub run, failing test message, and matching receiver report | ____________________ |
| Fixed GitHub run and matching receiver report | ____________________ |
| Optional Pages unchanged-after-failure evidence | ____________________ |
| Optional received pass/fail emails | ____________________ |

## 7. Blank evidence record

**Status before your GitHub demonstration:** no personal push-run evidence entered. `—` means unfilled, not passed. Do not guess counts, names, timestamps, or statuses.

| Observation | Passing baseline | Broken validation | Fixed validation |
| --- | --- | --- | --- |
| Repository URL | — | — | — |
| Branch | — | — | — |
| Full commit SHA | — | — | — |
| GitHub run ID | — | — | — |
| GitHub run URL | — | — | — |
| GitHub test step/job status | — | — | — |
| Receiver report UTC timestamp | — | — | — |
| Actual total / passed / failed | — | — | — |
| Actual test names and results | — | — | — |
| Actual failure message, if any | — | — | — |
| Report overall status | — | — | — |
| Sender delivery outcome | — | — | — |
| Report artifact reference | — | — | — |
| Preserved receiver JSON path | — | — | — |
| Screenshot references | — | — | — |
| Optional Pages deployed revision/status | — | — | — |
| Optional email receipt/reference | — | — | — |

### Submission record

- Repository URL: ____________________
- README setup section/reference: ____________________
- Evidence location: ____________________
- Pages bonus attempted? ____________________
- Pages URL, if attempted: ____________________
- Email bonus attempted? ____________________
- Pass/fail email evidence, if attempted: ____________________
- Any requirement not demonstrated, with reason: ____________________

Submit the repository URL, setup instructions, and evidence. Add the Pages URL and email evidence only for bonuses actually attempted. Report missing external proof honestly rather than calling setup or a simulation a successful demonstration.
