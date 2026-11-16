# Viva guide: Assignment Submission Portal

**CSC418 DevOps lab mid — COMSATS Attock**  
**Instructor:** Babar Shazad  
**Assessment:** 40 core marks + 10 optional bonus marks

These answers explain the project contract and implementation. Local verification is recorded in `LOCAL_VERIFICATION.md`; GitHub pushes and bonuses require your own setup and evidence. When asked for proof, open the corresponding actual code, test output, GitHub run, and received report.

## A 60-second explanation

> My project is an assignment submission portal using Python 3.10 or newer and only the standard library. Students enter their name, registration number, assignment title, and submission URL. The local server validates the values, saves accepted submissions in SQLite, and shows a list; it does not upload files. Every GitHub push runs real unittest tests on a trusted local self-hosted runner. The tests cover a valid saved submission, missing registration, and an invalid URL. The runner writes actual results to a JSON report and exits unsuccessfully if tests fail. An always-run sender posts the report to a token-protected receiver on the same machine. I demonstrate a passing push, a real URL-validation defect, and a repair, matching each report to its commit SHA and run ID. Pages and pass/fail email are optional bonuses, not part of the core portal.

Use this as an explanation of the design. Say “I demonstrated” only after you have the actual evidence.

## 25 short project-focused questions and answers

### 1. What problem does your portal solve?

It records assignment submission links in one place. A student supplies a name, registration number, assignment title, and submission URL, then sees the accepted submission in the list.

### 2. Does it upload an assignment file?

No. It stores the submission URL, not the file behind the link. A valid URL format also does not prove that the linked assignment exists or is accessible.

### 3. What happens when a student submits the form?

The browser sends the fields to the local server. The server validates them, rejects invalid input without saving it, or saves valid input to SQLite. The browser then displays the saved list.

### 4. Why validate on the server if the browser checks fields?

Browser checks can be bypassed. Server validation protects stored data even when someone sends a request without using the form.

### 5. Which tools does the project need?

Python 3.10+, its standard library, Git, GitHub Actions, and a browser. Python provides the HTTP server, SQLite support, unittest, and networking tools. No third-party Python dependencies are required.

### 6. Where is the local submission data stored?

In `data/submissions.db`, a SQLite database. The browser's list should reflect the server's persisted data, not just an item temporarily appended on screen.

### 7. What are the exact three required test cases?

1. Valid submission is accepted, saved, and listed.
2. Missing registration number is rejected with a useful message and not saved.
3. Invalid submission URL is rejected and not saved.

Those are behavior descriptions. The exact test function names must be read from the actual suite/report.

### 8. How do you run the automated tests?

From the project directory, run `python3 scripts/run_tests.py`. It runs the real unittest suite, writes actual `<project root>/test-report.json` regardless of cwd, and exits unsuccessfully on failure/error. `--output` selects another report path; use sender `--report` for that same file.

### 9. What makes these real tests rather than simulated results?

They invoke the application behavior and assert the observed response, persistence, and list behavior. The report comes from unittest outcomes, not from printing a predefined “passed” message.

### 10. How does GitHub know that the tests failed?

The test command exits nonzero, making the test step/job fail. We must not hide it with `continue-on-error` or `|| true`.

### 11. What is the difference between a failure, an error, and a skip?

A failure means an assertion was not satisfied. An error means a test could not complete normally, such as an unexpected exception. A skip means a case was not run. Errors appear as `result: "error"`, count in `summary.failed`, and fail the run. Skips count in `summary.skipped`, not `summary.passed`; even an overall passed suite does not prove a skipped required case.

### 12. When does the CI workflow run?

On every push to the trusted repository. It must test branches as well as `main`; only the optional deployment is restricted to `main`. There is no `pull_request` trigger for this local self-hosted setup.

### 13. Why is the runner self-hosted and on the same machine?

The receiver is local. A runner on that same machine can reach `http://127.0.0.1:9000/report`, and it already has Python installed.

### 14. Why will localhost not reach my laptop from a GitHub-hosted runner?

Localhost means the machine making the request. On a GitHub-hosted runner, it points to GitHub's machine. Our local runner avoids that problem; a secured tunnel is an alternative, not a required tool here.

### 15. What does the `labmid` runner setting mean?

The runner is named and given the custom label `labmid`. The workflow selects labels such as `self-hosted` and `labmid`; the display name alone is not a scheduling label.

### 16. How is the report receiver authenticated?

`REPORT_TOKEN` is required when starting `receiver.py`. The sender uses the same value in `X-Report-Token`. GitHub stores it as `LOCAL_REPORT_TOKEN` and supplies it to the sender's `REPORT_TOKEN` environment variable. Do not commit or show the token.

### 17. Where does the receiver store its report, and why outside the checkout?

By default, it saves `test-report.json` in its startup working directory. Start it in `$HOME/labmid-reports` using the absolute receiver script path. GitHub checkout cleanup could delete an untracked report inside the runner workspace. Atomic replacement prevents a partially written latest report.

### 18. What must be included in the received JSON?

Top-level keys include `repository`, `branch`, `commit_sha`, `run_id`, `timestamp`, `tests`, and `summary`, with `schema_version: 1`. Tests have `name`, `result`, and `failure_message`; summary has `total`, `passed`, `failed`, `skipped`, and `status`. The UTC timestamp ends in `Z`. Open the real received JSON to show values matching the GitHub run.

### 19. Why are sender and artifact steps marked `always()`?

Normal later steps may be skipped after tests fail. `always()` lets the sender and artifact upload be attempted after a failed test, preserving failure evidence. It does not make the test pass, and it cannot guarantee delivery when the runner is offline or a report is missing.

### 20. How do you prove that the receiver got a new report?

Match its commit SHA and run ID to the GitHub run, check the UTC timestamp and outcomes, and preserve the received JSON. A healthy `/health` response or an old file is not evidence of new delivery.

### 21. How do you introduce and fix the demo defect?

Run `python3 scripts/demo_defect.py introduce` to disable URL validation in `validation.py`, then stage that file, commit, and push. The unchanged invalid-URL test should fail. Run `python3 scripts/demo_defect.py fix`, stage `validation.py`, commit, and push again to show the restored passing result. Do not edit the JSON to fake a failure.

### 22. What is the difference between CI, CD, and deployment?

**CI** automatically integrates/checks changes with tests. **Continuous delivery** keeps a tested release ready, often with a manual release decision. **Continuous deployment** automatically releases eligible successful changes. **Deployment** is the action of publishing a version. Our core is CI plus report delivery; automatic successful-main Pages publishing is an optional deployment stage.

### 23. How is the Pages bonus made safe, and can it run the backend?

Pages is opt-in using repository variable `ENABLE_PAGES=true`, only on `main`, after the same revision's tests/report job succeeds. A failed revision must leave the previous deployment unchanged. Pages hosts static files, not Python or SQLite. Its clearly labelled demo uses browser `localStorage`, separate from local server data. Private repositories on a free plan may not support Pages; keep the trusted runner private and skip the bonus or use an eligible plan rather than exposing it to untrusted public code.

### 24. How do the optional pass/fail emails work?

Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`, and the recipient `SMTP_TO` as secrets. Use the provider's supported TLS mode, normally STARTTLS on 587 or implicit TLS on 465. Send both test outcomes and prove actual receipt; missing configuration or a queued step is not proof of delivered email.

### 25. What should you submit, and what should you not claim?

Submit the repository URL, README setup instructions, and actual pass/break/fix evidence. Include a Pages URL and received pass/fail email evidence if attempting bonuses. Do not claim GitHub, receiver delivery, Pages, or email was verified when you only prepared code or instructions.

## Common pitfalls to mention in the viva

| Pitfall | Correct explanation |
| --- | --- |
| “The frontend rejects it, so storage is safe.” | Server-side validation must also reject invalid requests. |
| “The test printed PASS.” | Show assertions against real app behavior and actual runner outcomes. |
| “Invalid input gives an error, so the test is enough.” | Also verify the invalid record was not saved or listed. |
| “The suite is green, so all cases ran.” | Check skips/errors and that the three required cases executed. |
| “`always()` turns the job green.” | It runs follow-up steps; it does not hide earlier failure. |
| “The workflow was queued, so the report arrived.” | Keep runner/receiver alive and match the received SHA/run ID. |
| “Localhost points to my laptop everywhere.” | It points to the machine making the request. |
| “Store the receiver report beside the runner checkout.” | Use a separate startup directory to survive checkout cleanup. |
| “Pages has the same shared SQLite data.” | Pages uses a separate browser-local static demo. |
| “A feature-branch pass can deploy `main`.” | Deployment requires `main` and successful checks of that same revision. |
| “Any public self-hosted runner is safe.” | Use a private trusted repository; untrusted code can execute on the host. |
| “SMTP secrets prove notification.” | Show actual received pass and fail messages. |
| “Every report has these guessed JSON keys.” | Read the actual schema and values before explaining them. |

## A small evidence-first viva routine

1. Explain the local form-to-SQLite lifecycle.
2. Show the three required cases and their actual test names/results.
3. Open the failing GitHub run and show that tests failed but report delivery still ran.
4. Open its received report and match SHA/run ID.
5. Show the repair run and new report.
6. Demonstrate bonuses only if actually configured and observed.
