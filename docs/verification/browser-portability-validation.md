Browser portability overlay: staged only; no browser or service was started.

The default config uses the installed Playwright-managed browser. Set
`TOGETHERMOVE_BROWSER_PATH` to an explicit executable when desired. The Mac
config also accepts that override, otherwise uses system Chrome if present,
then falls back to Playwright's managed browser. This does not install a browser.

Both configs and the browser specs write only project-local `test-results/browser/`
by default. Set `TOGETHERMOVE_QA_OUTPUT_DIR` for the browser spec capture directory.
The historical external baseline suite is included only when explicitly selected
with `TOGETHERMOVE_BASELINE_DIR`; relative values resolve from the project root.

The stale synthetic-persistence assertions now expect the current app's zero
saved moments and byte-identical localStorage after the authored six-ray input.
The camera-source swap after completion still tests retention of the frozen
synthetic result label. Manual persistence tests are unchanged.

After copying the overlay, the parent should run Node unit tests and
`npx playwright test --list --config playwright.mac.config.js`, then perform an
actual browser run of the mocked `motion` project. The `live-synthetic` project
needs a separately started explicit synthetic sidecar; it does not start one.
An actual browser run remains required to validate these staged UI assertions.
