# Local verification — final project

The final project was checked on Linux with Python 3.12.3. It uses the Python standard library and targets Python 3.10 or newer.

## Real passing, failing, and corrected runs

These are **local execution results, not GitHub Actions results**. The complete project was copied to an isolated temporary directory. The unchanged test suite was executed in three states, and each resulting report was sent over a real loopback HTTP connection to the project receiver. Receiver output was read back and compared with the generated report.

| State | Total | Passed | Failed | Skipped | Test exit code | HTTP delivery |
|---|---:|---:|---:|---:|---:|---|
| Original working validation | 37 | 37 | 0 | 0 | 0 | Received; JSON matched |
| Actual URL-validation bypass | 37 | 36 | 1 | 0 | 1 | Received; JSON matched |
| Validation restored | 37 | 37 | 0 | 0 | 0 | Received; JSON matched |

The deliberately broken application failed `test_portal.PortalTests.test_invalid_url_is_rejected`. The failure came from actual assertions against HTTP responses and the saved-submissions list; the test expectations and report were not altered to produce it. The defect was introduced and repaired only in the isolated project copy. The delivered `validation.py` remains correct.

The three PDF-required cases have explicit test names:

- `test_portal.PortalTests.test_valid_submission_saves_and_lists`
- `test_portal.PortalTests.test_missing_registration_number_is_rejected`
- `test_portal.PortalTests.test_invalid_url_is_rejected`

The invalid-input tests also check that rejected input is not in the stored submission list.

### Actual evidence files

See [verification.json](evidence/local-final/verification.json) for the machine-readable summary. For each state, the folder contains actual generated JSON, receiver-saved JSON, test output, and sender output:

- [Passing received JSON](evidence/local-final/pass-before-received.json)
- [Failing received JSON](evidence/local-final/real-defect-fail-received.json)
- [Corrected received JSON](evidence/local-final/fixed-pass-received.json)

The repository, branch, commit SHA and run ID are deliberately `null` in these local reports because this folder has not been committed/pushed or executed on GitHub. The timestamps and test results are real. On GitHub, the runner reads the corresponding actual `GITHUB_*` values. No GitHub metadata was invented.

## Other checks

- The real browser showed the local-server mode, rejected missing/invalid submission URLs, saved a valid HTTP/HTTPS submission, and displayed it in the saved list.
- The portal layout was checked in a browser viewport.
- The Pages-compatible static demo was served locally, correctly identified itself as browser-only, saved a valid submission, and kept it after reloading. This does not establish a live GitHub Pages deployment.
- The automated suite checks SQLite persistence after a server restart, required fields, invalid URLs, malformed/oversized requests, and isolated test storage.
- Receiver tests verify authentication, malformed/inconsistent-report rejection, and preservation of the previous report after invalid input.
- Reporting tests verify success, assertion failures, unexpected errors, import/discovery problems, subtest failures, skips and exit codes.
- Email construction and TLS sequencing are tested with mocks. **No live email was sent.**
- Frontend JavaScript passed `node --check`.
- Workflow YAML parsed successfully, and its push trigger and local-runner labels were checked. This is **not** a substitute for executing it on GitHub.
- The 11-page PDF guide passed automated PDF checks and rendered-page inspection.

## Not yet demonstrated

Your account is still needed to create/push the GitHub repository, start the receiver and tunnel,
configure secrets, and collect the actual three GitHub run URLs and received reports. GitHub Pages
deployment and received email are also not verified externally. Follow [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md)
for those assessed demonstrations.
