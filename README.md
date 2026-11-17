# Assignment Portal — DevOps LabMid

A small assignment-submission portal with real automated tests, a GitHub Actions pipeline, and automatic test-report delivery to your computer. Built for the attached CSC418 lab-mid requirements.

**Start here:** run the portal locally, read [the simple explanation](docs/EXPLAINED.md), then configure the receiver and GitHub runner. Revise with [the viva guide](docs/VIVA_GUIDE.md), or use the [printable project and viva guide](docs/DevOps-LabMid-Guide.pdf).

**Verified locally:** 37 tests pass. Introducing the real URL-validation defect gives 36 passes and 1 failure; repairing it restores 37 passes. The real receiver received and saved all three reports. See [the local verification record](docs/LOCAL_VERIFICATION.md). This does not replace your own GitHub demonstration.

## What you get

- Student name, registration number, assignment title, and submission-link form.
- Server-side required-field and HTTP/HTTPS URL validation.
- SQLite persistence and a saved-submissions list. No file upload required.
- Real Python `unittest` results in JSON; failed tests return a failing exit code.
- Authenticated local report receiver, automatic delivery after passing **and failing** runs.
- GitHub Actions on every push, using a GitHub-hosted runner and a secure tunnel to the local receiver.
- Optional static GitHub Pages demo and SMTP email reports.

**Only Python 3.10+ and Git are needed for the core project.** There is no Flask, npm build, Docker, cloud database, or Python package installation. This is a local educational application, not a production multi-user system.

## 1. Run the app

Extract the project and open a terminal inside `assignment-portal`:

```bash
python3 --version
python3 server.py
```

Open **http://127.0.0.1:8000**. Enter a name, registration number, assignment title, and a URL such as `https://example.com/assignment1`. Saved entries go into `data/submissions.db` and remain after restarting the application. Press Ctrl+C to stop.

On Windows, use `py -3` in place of `python3` for local commands if necessary. The supplied CI file expects a Linux/macOS runner with the command `python3` available.

## 2. Run real automated tests

From the project folder:

```bash
python3 scripts/run_tests.py
```

This executes the test suite, prints the results, writes `test-report.json`, and returns exit code 0 only when the run is successful. The report is **not a hand-written summary**. Each case comes from the actual execution of a test. Tests use temporary databases; they do not erase your portal data.

The three required cases check that:

1. A complete valid submission is saved and appears in the list.
2. A missing registration number is rejected with a message.
3. An invalid URL is rejected and is not saved.

Additional tests cover persistence, malformed requests, report handling, and failure reporting.

## 3. Start the receiver in a separate directory

The receiver is a second program, independent of the portal. It listens for test reports on port 9000 and saves the most recent report on your computer.

**Important:** keep its report directory outside the GitHub runner's checkout. GitHub checkout cleans the workspace; that must not delete the instructor's local record.

Linux/macOS example — replace `/absolute/path/assignment-portal` with the real extracted path:

```bash
mkdir -p "$HOME/labmid-reports"
cd "$HOME/labmid-reports"
export REPORT_TOKEN="replace-with-a-long-random-private-token"
python3 /absolute/path/assignment-portal/receiver.py
```

Generate a token locally if desired:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Keep the token private. Use the **same value** for the GitHub secret `LOCAL_REPORT_TOKEN` below. Never commit it. Keep this terminal running throughout the demonstration.

Windows PowerShell equivalent:

```powershell
New-Item -ItemType Directory -Force "$HOME\labmid-reports"
Set-Location "$HOME\labmid-reports"
$env:REPORT_TOKEN = "replace-with-a-long-random-private-token"
py -3 C:\absolute\path\assignment-portal\receiver.py
```

Health check: **http://127.0.0.1:9000/health**. This endpoint checks that the receiver is alive; it is not itself a test report.

### Check automatic local delivery before GitHub setup

Open a **second terminal in the project directory**, leaving the receiver running:

```bash
export REPORT_TOKEN="the-same-private-token"
python3 scripts/run_tests.py
python3 scripts/send_report.py
```

The sender makes a real HTTP POST to `http://127.0.0.1:9000/report`. The receiver automatically saves `~/labmid-reports/test-report.json`. You do not download or copy the file manually. On PowerShell, set `$env:REPORT_TOKEN` and replace `python3` with `py -3`.

## 4. Put the project on GitHub

Create an empty **private GitHub repository** named `assignment-portal` in your own account. Do not initialize it with another README. From the project folder:

```bash
git init
git branch -M main
git add .
git commit -m "Add assignment portal with DevOps pipeline"
git remote add origin https://github.com/YOUR_USERNAME/assignment-portal.git
git push -u origin main
```

Use your own username. Configure Git name/email if Git asks. Authenticate using GitHub's supported credential mechanism; never put a personal access token in source files.

The workflow requires the `LOCAL_REPORT_TOKEN` and `REPORT_RECEIVER_URL` secrets before report
delivery can succeed. The project has not been published to GitHub on your behalf; these steps
require your account.

## 5. Configure GitHub Actions and the tunnel

The workflow uses a GitHub-hosted Ubuntu runner, with separate `test-and-report` and
`send-email` jobs. A hosted runner's `localhost` is not your computer, so the local
receiver must be exposed through an authenticated tunnel or relay.

1. Start the receiver from the separate reports directory described above.
2. Start a tunnel provider of your choice and forward its HTTPS URL to `http://127.0.0.1:9000`.
   Keep the tunnel running for every demonstration push. Do not expose the receiver without
   its token check.
3. In **Settings → Secrets and variables → Actions → Secrets**, add:

| Secret | Value |
|---|---|
| `LOCAL_REPORT_TOKEN` | The same private value used by the receiver's `REPORT_TOKEN` |
| `REPORT_RECEIVER_URL` | The tunnel's HTTPS `/report` URL |

The workflow installs Python through `actions/setup-python`; this standard-library project
does not need Flask or any other package installation. The portal terminal is needed to show
the web app but is not required by the tests.

## 6. Demonstrate pass, fail, and fix

Follow [the complete demo checklist](docs/DEMO_CHECKLIST.md). Once the receiver and runner are online:

```bash
# Passing revision: changes to documentation still trigger all tests.
git commit --allow-empty -m "Demo: passing test run"
git push

# Real defect: deliberately bypass URL validation.
python3 scripts/demo_defect.py introduce
git add validation.py
git commit -m "Demo: introduce URL validation defect"
git push

# Corrected revision: restore the validation.
python3 scripts/demo_defect.py fix
git add validation.py
git commit -m "Demo: restore URL validation"
git push
```

**Wait for each run to finish and capture its evidence before the next push.** In the broken run, the invalid-URL test must fail, the test step must be red, and the receiver must still receive the failing JSON. After the fix, the test step and report return to passing. Do not leave the intentional defect in your final submission.

The pipeline uploads the report with `if: always()` and runs the `send-email` job with
`if: always()`, so a normal test failure does not skip report delivery. An unavailable
receiver or tunnel cannot guarantee delivery; keep both services running. The sender fails
visibly if delivery fails instead of hiding the problem.

## 7. Optional bonus: GitHub Pages

The main app has a Python backend and SQLite. **GitHub Pages cannot run them.** The optional Pages deployment publishes only `static/`, which switches to a clearly labelled **static browser-local demo**. Its submissions use that browser's localStorage, not the server database; other students and browsers do not share them. This is permitted by the assignment's static-demo bonus.

1. Confirm your repository/account plan supports GitHub Pages for your repository visibility. Private repositories may require a paid plan; do not make a self-hosted-runner repository public casually.
2. Open **Settings → Pages** and choose **GitHub Actions** as the source.
3. In **Settings → Secrets and variables → Actions → Variables**, add `ENABLE_PAGES` with value `true`.
4. Push a passing revision to `main`, or manually run the workflow for the `main` branch.
5. Open the `github-pages` deployment/environment to find the actual published URL.

The `deploy-pages` job is optional and runs only when `ENABLE_PAGES=true`, the push is to
`main`, and the test/report/email jobs succeed. A failed test or report delivery therefore
leaves the previously deployed version unchanged.

## 8. Optional bonus: email reports

Configure your email provider's SMTP settings in **GitHub Actions secrets**:

| Secret | Meaning |
|---|---|
| `SMTP_HOST` | Provider's SMTP hostname |
| `SMTP_PORT` | Usually `587` for STARTTLS or `465` for implicit TLS |
| `SMTP_USERNAME` | SMTP login |
| `SMTP_PASSWORD` | SMTP/app password; never commit it |
| `SMTP_FROM` | Sender address permitted by your provider |
| `SMTP_TO` | Configurable recipient address |

Use the credentials and TLS port supported by your provider. Many providers need an app password rather than the normal account password. The optional step sends actual test results and attaches JSON after both passing and failing test runs. It runs automatically when SMTP is configured. Without configuration, it is skipped. A network or authentication failure is reported as a failed email step.

No live emails have been sent and no credentials are supplied with the project.

## Troubleshooting

| Symptom | Check |
|---|---|
| Report delivery fails | Check the tunnel, receiver health, `REPORT_RECEIVER_URL`, and matching token. |
| Report connection refused | Receiver is running on the same machine/environment as the worker, on port 9000. |
| Receiver rejects authentication | `LOCAL_REPORT_TOKEN` equals the receiver's `REPORT_TOKEN`. |
| No report after failed test | The send step ran with `always()`; inspect its output, receiver health, and output-directory permissions. |
| Receiver file disappeared | Receiver output must be outside the runner checkout. |
| Address already in use | Stop your own previous instance or choose another documented port; do not kill unrelated processes. |
| Pages job skipped | Enable `ENABLE_PAGES=true`, push to `main`, and pass the core job. |
| Pages demo has different submissions | Expected: localStorage and the local SQLite database are separate. |
| Email authentication failed | Verify SMTP secrets, provider policy, app password, and TLS port. |

## Files and what they do

```text
server.py                    Portal backend, SQLite and HTTP API
validation.py                Required-field and URL validation
http_support.py              Shared JSON request/response handling
reporting.py                 Report schema checks and atomic JSON writing
receiver.py                  Authenticated localhost JSON report receiver
static/                      Portal UI and Pages-compatible static demo
tests/                       Executable automated test cases
scripts/run_tests.py         Runs tests and builds actual-result JSON
scripts/send_report.py       Automatically POSTs JSON to the receiver
scripts/email_report.py      Optional SMTP report email
scripts/demo_defect.py       Introduces/restores one deliberate validation defect
.github/workflows/ci.yml      Push-triggered CI and optional bonus automation
docs/EXPLAINED.md            Beginner-friendly explanation
docs/VIVA_GUIDE.md           Viva questions and answers
docs/DEMO_CHECKLIST.md       Pass/fail/fix evidence instructions
docs/REQUIREMENTS.md         Assignment coverage and honest limitations
```

## Submission checklist

Submit your own repository URL, this setup guide, and **actual GitHub** passing, failing, and corrected run evidence with the automatically updated local JSON for each. Include the deployed Pages URL and received-email evidence only if you enabled and demonstrated those bonuses.

Local verification is useful, but it is **not a replacement** for your required three GitHub pushes. No repository URL, cloud pipeline result, deployed URL, or received email should be claimed until it exists.
# devops-labmid
