# Test Infrastructure Specification: Hamrah Bagherololum Copy (PWA & Android TWA)

## 1. Test Philosophy

### 1.1 Opaque-Box & Requirement-Driven Testing
All tests in this suite operate strictly on an **opaque-box** (black-box) paradigm driven directly by the authoritative requirements specified in `ORIGINAL_REQUEST.md` and architectural interface contracts defined in `PROJECT.md`.
- Tests verify observable properties: file existence, file permissions, strict syntax/schema compliance, HTTP endpoint response contracts, cryptographic fingerprint fidelity, DOM manipulation behavior, and build pipeline definitions.
- Tests NEVER test internal accidental implementation details. Every assertion verifies an observable contract mandated by the requirements (e.g., Persian RTL layout, SHA-256 certificate matching, Cafe Bazaar TWA metadata, Network-First caching headers, and admin element purge).

### 1.2 Determinism & Zero External Dependencies
- The test suite is implemented in pure Python (standard library: `unittest`, `json`, `re`, `pathlib`, `hashlib`, `urllib`, `xml.etree.ElementTree`, `zipfile`, `shutil`, `argparse`).
- It requires no third-party packages (no `pytest`, no `requests`, no `playwright`), guaranteeing 100% determinism across local Windows environments and headless Linux CI/CD runners (`ubuntu-latest`).

### 1.3 Progressive Testability & Fail-Fast Signals
- Tests are organized across four modular tiers:
  - **Tier 1**: Feature Coverage Tests (Features 1–26).
  - **Tier 2**: Boundary, Edge Case, & Adversarial Input Tests.
  - **Tier 3**: Cross-Feature Integration & Contract Verification.
  - **Tier 4**: Real-World Application & Consumer Persona Scenarios.
- The test runner supports granular filtering (`--tier`, `--milestone`, `--feature`), enabling agents and CI runners to execute specific subsets as milestones are implemented. Missing artifacts produce unambiguous, actionable failure diagnostics indicating which milestone feature needs attention.

---

## 2. Feature Inventory (Features 1–28)

| Feature # | Feature Name | Milestone | Authoritative Source | Primary Verification Target |
|---|---|---|---|---|
| **F-01** | Copy Isolation & Persian Layout | M1 | `ORIGINAL_REQUEST §R1` | `index.html` `lang="fa"`, `dir="rtl"`, Persian typography, isolated repo origins |
| **F-02** | Production URL Sanitization | M1 | `ORIGINAL_REQUEST §R1` | Absence of production URLs; presence of copy Worker & Pages endpoints |
| **F-03** | Release Keystore Generation | M1 | `ORIGINAL_REQUEST §R4` | `android.keystore` existence, RSA 2048-bit, 10,000-day validity |
| **F-04** | Keystore Documentation | M1 | `ORIGINAL_REQUEST §R4` | `KEYSTORE_CREDENTIALS.txt` alias, passwords, uppercase SHA-256 fingerprint |
| **F-05** | Digital Asset Links Schema | M1 | `ORIGINAL_REQUEST §R4` | `/.well-known/assetlinks.json` dual Google + Cafe Bazaar relation statements |
| **F-06** | Cloudflare & Pages Asset Serving | M1 | `ORIGINAL_REQUEST §R4` | `.nojekyll` existence, `wrangler.json` asset routing, CORS `*` headers |
| **F-07** | Early App Mode Detection | M2 | `ORIGINAL_REQUEST §R2` | Inline `<head>` script detecting `?mode=app`, `?source=twa`, `localStorage` flag |
| **F-08** | Anti-FOUC CSS Shield | M2 | `ORIGINAL_REQUEST §R2` | Injected CSS hiding `#header-admin-btn`, `[data-admin-trigger]`, and staff modals |
| **F-09** | DOM Admin Button Removal | M2 | `ORIGINAL_REQUEST §R2` | Physical DOM removal of `#header-admin-btn` on page load in app mode |
| **F-10** | Dynamic Header Protection | M2 | `ORIGINAL_REQUEST §R2` | `AuthService.updateHeaderBadges()` intercepted to prevent admin button recreation |
| **F-11** | Admin Route & Modal Interceptor | M2 | `ORIGINAL_REQUEST §R2` | Route guard blocking `navigateTo('admin')` and `openStaffLoginModal()` in app mode |
| **F-12** | Standard Web Mode Preservation | M2 | `ORIGINAL_REQUEST §R2` | In web mode (or `?mode=web`), admin login button and modal remain fully accessible |
| **F-13** | High-Resolution App Icons | M3 | `ORIGINAL_REQUEST §R3` | Crisp PNG icons in `icons/` (192, 512, maskable) with valid byte signatures |
| **F-14** | Web App Manifest Configuration | M3 | `ORIGINAL_REQUEST §R3` | Valid `manifest.json`, Persian title, `start_url: "./?mode=app"`, `standalone` |
| **F-15** | Real-Time Sync Service Worker | M3 | `ORIGINAL_REQUEST §R3` | `sw.js` Network-First (`cache: 'no-store'`) for navigation and dynamic APIs |
| **F-16** | Persian RTL Offline Fallback | M3 | `ORIGINAL_REQUEST §R3` | Standalone `offline.html`, Persian text, RTL dir, dark navy theme, retry button |
| **F-17** | Service Worker Registration | M3 | `ORIGINAL_REQUEST §R3` | Robust service worker registration script present in `index.html` |
| **F-18** | Mobile UI Polish & Ergonomics | M3 | `ORIGINAL_REQUEST §R3` | `user-select: none`, `-webkit-tap-highlight-color: transparent`, `overflow-x: hidden` |
| **F-19** | Hardware Back Button Modal Handling | M3 | `ORIGINAL_REQUEST §R3` | History API `popstate` listener dismissing active modal dialogs |
| **F-20** | Android TWA Project Architecture | M4 | `ORIGINAL_REQUEST §R5` | `android/` project tree, `compileSdk 35`, `targetSdk 34`, `minSdk 24`, package `ir.bagherololum.hamrah` |
| **F-21** | Cafe Bazaar TWA Manifest Config | M4 | `ORIGINAL_REQUEST §R5` | `LauncherActivity`, `DEFAULT_URL` metadata with `?mode=app`, Persian label |
| **F-22** | Multi-Origin Fallback Config | M4 | `ORIGINAL_REQUEST §R5` | `ADDITIONAL_TRUSTED_ORIGINS` referencing GitHub Pages fallback mirror |
| **F-23** | Local Signed APK & AAB Build | M4 | `ORIGINAL_REQUEST §R5` | Signed `hamrah-bagherololum-release.apk` and `.aab` in `release-apk/` |
| **F-24** | GitHub Actions CI/CD Workflow | M5 | `ORIGINAL_REQUEST §R5` | `.github/workflows/build-android-apk.yml` push to `main`, JDK 17, Android SDK |
| **F-25** | Artifact Upload & GitHub Release | M5 | `ORIGINAL_REQUEST §R5` | Action steps uploading signed APK/AAB and creating GitHub Release with Persian notes |
| **F-26** | Git Commit, Push & Worker Deploy | M5 | `ORIGINAL_REQUEST §R1, R5` | Clean git status, tracking `main` on copy repo, worker deployment setup |
| **F-27** | Full E2E Test Suite (Tiers 1–4) | M6 | `ORIGINAL_REQUEST Acceptance Criteria` | Standalone Python test runner executing Tiers 1–4 with 100% pass signal |
| **F-28** | Adversarial Coverage Hardening | M6 | `PROJECT.md §Milestones` | Robustness stress tests, malformed query injection, boundary fuzzing |

---

## 3. Test Architecture

### 3.1 Directory Layout
```
hamrah-bagherololum-copy/
├── TEST_INFRA.md                 # This test infrastructure document
├── TEST_READY.md                 # Publication signal and coverage report
└── tests/
    ├── __init__.py               # Python package initialization
    ├── run_e2e_tests.py          # Unified test CLI runner and reporter
    ├── test_tier1_features.py    # Tier 1: Comprehensive Feature Coverage (Features 1–26)
    ├── test_tier2_boundaries.py  # Tier 2: Boundary, Edge Case, & Malformed Input Tests
    ├── test_tier3_combinations.py# Tier 3: Cross-Feature Integration & Contract Verification
    └── test_tier4_scenarios.py   # Tier 4: Real-World End-to-End Application Scenarios
```

### 3.2 Invocation Commands
```bash
# Run entire test suite (Tiers 1 through 4)
python tests/run_e2e_tests.py

# Run specific tier
python tests/run_e2e_tests.py --tier 1
python tests/run_e2e_tests.py --tier 2
python tests/run_e2e_tests.py --tier 3
python tests/run_e2e_tests.py --tier 4

# Run specific milestone features
python tests/run_e2e_tests.py --milestone M1
python tests/run_e2e_tests.py --milestone M2

# Run specific feature by ID
python tests/run_e2e_tests.py --feature F-05

# Output machine-readable JSON results
python tests/run_e2e_tests.py --json

# Verbose inspection mode
python tests/run_e2e_tests.py -v
```

### 3.3 Pass/Fail Semantics & Exit Codes
- **Exit Code 0**: All executed test assertions passed successfully.
- **Exit Code 1**: One or more assertions failed (e.g., missing expected file, invalid schema, contract mismatch).
- **Exit Code 2**: Execution syntax error or missing runner arguments.

---

## 4. Real-World Application Scenarios (Tier 4)

### Scenario 1: End-to-End Student Navigation in Android App Mode
- **Persona**: Student opening the installed Android TWA application from home screen.
- **Trigger**: Launch URL `https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/?mode=app`.
- **Flow**:
  1. Early app mode guard executes before DOM rendering, sets `HAMRAH_APP_MODE=1` in `localStorage`, and appends `is-mobile-app` class to `<html>`.
  2. CSS shield instantly hides `#header-admin-btn` and all `[data-admin-trigger]` elements (zero FOUC).
  3. Physical DOM cleanup removes the admin button nodes from the DOM tree.
  4. Subsequent student interactions (viewing quizzes, FAQs, majors) execute normally in Persian RTL.
  5. If the student attempts to invoke `navigateTo('admin')` or `openStaffLoginModal()` via console or direct hash navigation (`#admin`), the route interceptor catches the attempt and returns them to the home view.

### Scenario 2: Administrator Desktop Workflow with Real-Time Dynamic Sync
- **Persona**: School administrator updating counseling advice from a desktop browser.
- **Trigger**: Access `https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/?mode=web` (or standard browser view without mode parameters).
- **Flow**:
  1. App mode guard confirms absence of `mode=app` and clears `HAMRAH_APP_MODE`.
  2. `#header-admin-btn` is rendered and fully visible.
  3. Clicking `#header-admin-btn` opens the staff login modal without interception.
  4. Dynamic API requests (`db.json`, `/api/`) are fetched through `sw.js` with `cache: 'no-store'`, guaranteeing that updates published in the admin panel are delivered fresh without stale cache delay.

### Scenario 3: Cafe Bazaar Automated Ingestion Robot Validation
- **Persona**: Cafe Bazaar automated verification crawler evaluating uploaded APK.
- **Trigger**: Ingestion crawler inspects APK `AndroidManifest.xml` and fetches `/.well-known/assetlinks.json`.
- **Flow**:
  1. Crawler extracts `DEFAULT_URL` metadata (`https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/?mode=app`).
  2. Crawler requests `GET https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/.well-known/assetlinks.json`.
  3. Server responds with HTTP 200, `Content-Type: application/json`, and `Access-Control-Allow-Origin: *`.
  4. Crawler verifies the presence of statement with `relation: ["cafebazaar_twa"]` (and `handle_all_urls`).
  5. Crawler validates that `target.package_name` is exactly `ir.bagherololum.hamrah` and that `sha256_cert_fingerprints` matches the signing certificate extracted from the uploaded APK.
  6. Ownership verification succeeds automatically; the APK is approved without address bar warning.

### Scenario 4: Sub-optimal Connectivity & Offline Fallback Experience
- **Persona**: Student traveling with disrupted mobile connectivity.
- **Trigger**: Student opens app or taps navigation link while device is completely offline.
- **Flow**:
  1. Service Worker intercepts navigation request (`fetch(event.request)`).
  2. Network fetch fails with network timeout or disconnection.
  3. Service Worker catches failure and returns pre-cached `offline.html`.
  4. User is presented with a Persian RTL message explaining the connection loss and providing a prominent "تلاش مجدد" (Retry) button.
  5. Tapping "تلاش مجدد" re-triggers `window.location.reload()`, gracefully restoring the app when connectivity returns.

### Scenario 5: GitHub Actions CI/CD Headless Build & Release Pipeline
- **Persona**: Continuous Integration runner executing automated pipeline on push to `main`.
- **Trigger**: Git push event on branch `main`.
- **Flow**:
  1. Workflow file `.github/workflows/build-android-apk.yml` triggers on `ubuntu-latest`.
  2. Runner sets up JDK 17 and Android SDK platforms 34/35.
  3. Runner reads keystore credentials, compiles Android TWA, and signs release `.apk` and `.aab`.
  4. Artifact upload step preserves binaries as workflow artifacts.
  5. Automated release step tags the commit and publishes a GitHub Release containing both signed binaries and Persian release notes.

---

## 5. Coverage Thresholds

| Metric | Target Requirement | Suite Guarantee |
|---|---|---|
| **Tier 1: Feature Coverage** | $\ge 5$ explicit assertions per feature across all 26 features | **$\ge 130$ total assertions** |
| **Tier 2: Boundary & Corner Cases** | $\ge 5$ edge/boundary assertions per feature area | **$\ge 40$ edge tests** |
| **Tier 3: Cross-Feature Integration** | Pairwise integration tests covering all inter-milestone contracts | **$\ge 10$ multi-feature scenarios** |
| **Tier 4: Application Scenarios** | $\ge 5$ real-world consumer persona scenarios | **5 full-lifecycle application journeys** |
| **Pass Requirement** | 100% of implemented features must pass without skips or warnings | **Zero-tolerance verification** |
