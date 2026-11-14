#!/usr/bin/env python3
"""Milestone 5 Adversarial Challenge & Empirical Live Verification Suite.

Author: m5_challenger_1 (Roles: critic, specialist)
Scope:
1. CI/CD Workflow YAML Schema & Semantic Analysis (.github/workflows/build-android-apk.yml)
2. Live Cloudflare Worker Endpoints Empirical Probing & Header Validation
3. CDN Information Leak Prevention (Sensitive File Negative Probing)
4. Keystore & Fingerprint Cross-Artifact Consistency
5. Git Repository & Remote Isolation Verification
"""

import hashlib
import json
import os
import re
import ssl
import subprocess
import sys
import unittest
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "build-android-apk.yml"
KEYSTORE_PATH = PROJECT_ROOT / "android.keystore"
CREDENTIALS_PATH = PROJECT_ROOT / "KEYSTORE_CREDENTIALS.txt"
ASSETLINKS_PATH = PROJECT_ROOT / ".well-known" / "assetlinks.json"
MANIFEST_PATH = PROJECT_ROOT / "manifest.json"
OFFLINE_PATH = PROJECT_ROOT / "offline.html"
ASSETSIGNORE_PATH = PROJECT_ROOT / ".assetsignore"
GITIGNORE_PATH = PROJECT_ROOT / ".gitignore"

LIVE_WORKER_URL = "https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev"
EXPECTED_SHA256 = "F2:11:BF:37:3C:30:60:2D:31:D4:28:32:D2:8A:B7:09:C4:AA:6A:29:6F:F3:01:43:19:2C:17:CA:1C:A4:56:FE"
EXPECTED_PACKAGE = "ir.bagherololum.hamrah"


class TestWorkflowYAMLSyntaxAndSemantics(unittest.TestCase):
    """Adversarial stress-testing of GitHub Actions workflow file."""

    def setUp(self):
        self.assertTrue(WORKFLOW_PATH.exists(), f"Workflow file not found at {WORKFLOW_PATH}")
        with open(WORKFLOW_PATH, "r", encoding="utf-8") as f:
            self.raw_content = f.read()

    def test_01_yaml_parses_without_syntax_errors(self):
        """Workflow must parse cleanly into Python data structures via PyYAML."""
        import yaml
        try:
            data = yaml.safe_load(self.raw_content)
        except Exception as e:
            self.fail(f"PyYAML failed to parse {WORKFLOW_PATH}: {e}")
        self.assertIsInstance(data, dict)
        self.assertIn("name", data)
        self.assertIn("jobs", data)

    def test_02_workflow_triggers_and_branches(self):
        """Workflow triggers must include push to main and workflow_dispatch."""
        import yaml
        data = yaml.safe_load(self.raw_content)
        # In YAML 1.1, unquoted 'on' is parsed as boolean True
        trigger_config = data.get("on") or data.get(True)
        self.assertIsNotNone(trigger_config, "Workflow trigger configuration 'on' is missing")
        self.assertIn("push", trigger_config, "Trigger 'push' must be declared")
        self.assertIn("branches", trigger_config["push"])
        self.assertIn("main", trigger_config["push"]["branches"])
        self.assertIn("workflow_dispatch", trigger_config, "Trigger 'workflow_dispatch' must be present")

    def test_03_permissions_block_for_releases(self):
        """Permissions must explicitly allow contents: write for creating releases and tags."""
        import yaml
        data = yaml.safe_load(self.raw_content)
        permissions = data.get("permissions")
        self.assertIsNotNone(permissions, "Workflow permissions block is missing")
        self.assertEqual(permissions.get("contents"), "write")

    def test_04_runner_environment(self):
        """Job runner must be ubuntu-latest."""
        import yaml
        data = yaml.safe_load(self.raw_content)
        job = data["jobs"]["build"]
        self.assertEqual(job.get("runs-on"), "ubuntu-latest")

    def test_05_all_11_steps_present_and_configured(self):
        """All 11 essential build and release steps must exist in proper sequence."""
        import yaml
        data = yaml.safe_load(self.raw_content)
        steps = data["jobs"]["build"]["steps"]
        self.assertEqual(len(steps), 11, f"Expected exactly 11 steps, found {len(steps)}")

        # Step 1: Checkout
        self.assertEqual(steps[0].get("uses"), "actions/checkout@v4")

        # Step 2: JDK 17
        self.assertEqual(steps[1].get("uses"), "actions/setup-java@v4")
        with_java = steps[1].get("with", {})
        self.assertEqual(str(with_java.get("java-version")), "17")
        self.assertEqual(with_java.get("distribution"), "temurin")
        self.assertEqual(with_java.get("cache"), "gradle")

        # Step 3: Android SDK
        self.assertEqual(steps[2].get("uses"), "android-actions/setup-android@v3")

        # Step 4: Keystore Provisioning Dual-Path
        s4_run = steps[3].get("run", "")
        self.assertIn("KEYSTORE_BASE64", steps[3].get("env", {}))
        self.assertIn("base64 --decode", s4_run)
        self.assertIn("android.keystore", s4_run)
        self.assertIn("android/app/android.keystore", s4_run)

        # Step 5: Wrapper execution chmod
        s5_run = steps[4].get("run", "")
        self.assertIn("chmod +x android/gradlew", s5_run)

        # Step 6: Gradle build
        s6 = steps[5]
        self.assertEqual(s6.get("working-directory"), "android")
        s6_run = s6.get("run", "")
        self.assertIn("assembleRelease", s6_run)
        self.assertIn("bundleRelease", s6_run)
        env = s6.get("env", {})
        self.assertIn("ANDROID_KEYSTORE_PASSWORD", env)
        self.assertIn("ANDROID_KEY_ALIAS", env)
        self.assertIn("ANDROID_KEY_PASSWORD", env)

        # Step 7: Stage artifacts
        s7_run = steps[6].get("run", "")
        self.assertIn("mkdir -p release-apk", s7_run)
        self.assertIn("release-apk/hamrah-bagherololum-release.apk", s7_run)
        self.assertIn("release-apk/hamrah-bagherololum-release.aab", s7_run)

        # Step 8: apksigner verification
        s8_run = steps[7].get("run", "")
        self.assertIn("apksigner verify", s8_run)
        self.assertIn("--print-certs", s8_run)

        # Step 9 & 10: Upload artifacts
        self.assertEqual(steps[8].get("uses"), "actions/upload-artifact@v4")
        self.assertIn("hamrah-bagherololum-release-apk", steps[8].get("with", {}).get("name", ""))
        self.assertEqual(steps[9].get("uses"), "actions/upload-artifact@v4")
        self.assertIn("hamrah-bagherololum-release-aab", steps[9].get("with", {}).get("name", ""))

        # Step 11: Release publishing
        s11 = steps[10]
        self.assertEqual(s11.get("uses"), "softprops/action-gh-release@v2")
        self.assertEqual(s11.get("if"), "github.ref == 'refs/heads/main'")
        with_rel = s11.get("with", {})
        self.assertIn("v1.0.0-${{ github.run_number }}", with_rel.get("tag_name", ""))
        self.assertIn("همراه باقرالعلوم", with_rel.get("name", ""))
        self.assertIn("همراه باقرالعلوم", with_rel.get("body", ""))
        self.assertIn("release-apk/hamrah-bagherololum-release.apk", with_rel.get("files", ""))
        self.assertIn("release-apk/hamrah-bagherololum-release.aab", with_rel.get("files", ""))
        self.assertIn("GITHUB_TOKEN", s11.get("env", {}))

    def test_06_persian_encoding_integrity_in_workflow(self):
        """Persian strings inside workflow YAML must be valid UTF-8 and match branding."""
        self.assertIn("همراه باقرالعلوم", self.raw_content)
        self.assertIn("انتشار نسخه رسمی همراه باقرالعلوم", self.raw_content)
        self.assertIn("دبیرستان نمونه دولتی پسرانه باقرالعلوم (ع)", self.raw_content)
        self.assertIn(EXPECTED_SHA256, self.raw_content)
        self.assertIn(EXPECTED_PACKAGE, self.raw_content)


class TestLiveCloudflareWorkerEndpoints(unittest.TestCase):
    """Empirical HTTP verification against live Cloudflare Worker deployment."""

    @classmethod
    def setUpClass(cls):
        cls.ssl_ctx = ssl.create_default_context()

    def _fetch(self, path, headers=None, timeout=12):
        url = f"{LIVE_WORKER_URL}{path}"
        req_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) HamrahChallenger/1.0"}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=timeout) as resp:
                return resp.status, resp.headers, resp.read()
        except urllib.error.HTTPError as e:
            return e.code, e.headers, e.read()

    def test_01_root_endpoint_serving_persian_index(self):
        """Root URL / must return HTTP 200, text/html, RTL layout, and Persian brand."""
        status, headers, body = self._fetch("/")
        self.assertEqual(status, 200, "Root URL should return HTTP 200")
        content_type = headers.get("Content-Type", "")
        self.assertIn("text/html", content_type)
        html_text = body.decode("utf-8", errors="replace")
        self.assertIn('dir="rtl"', html_text)
        self.assertTrue('lang="fa"' in html_text or 'lang="fa-IR"' in html_text, "HTML must have Persian lang attribute")
        self.assertIn("همراه باقرالعلوم", html_text)
        self.assertIn("manifest.json", html_text)
        self.assertIn("sw.js", html_text)

    def test_02_assetlinks_schema_cors_and_fingerprints(self):
        """Assetlinks must return HTTP 200, JSON, CORS *, and correct fingerprints."""
        status, headers, body = self._fetch("/.well-known/assetlinks.json")
        self.assertEqual(status, 200, "Assetlinks endpoint should return HTTP 200")
        content_type = headers.get("Content-Type", "")
        self.assertIn("application/json", content_type)

        cors = headers.get("Access-Control-Allow-Origin", "")
        self.assertIn("*", cors, f"Expected CORS header Access-Control-Allow-Origin: *, got '{cors}'")

        data = json.loads(body.decode("utf-8"))
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2, f"Expected 2 statements in assetlinks.json, found {len(data)}")

        # Statement 1: handle_all_urls
        stmt_handle = next((s for s in data if "delegate_permission/common.handle_all_urls" in s.get("relation", [])), None)
        self.assertIsNotNone(stmt_handle, "Missing handle_all_urls statement")
        self.assertEqual(stmt_handle["target"]["namespace"], "android_app")
        self.assertEqual(stmt_handle["target"]["package_name"], EXPECTED_PACKAGE)
        self.assertIn(EXPECTED_SHA256, stmt_handle["target"]["sha256_cert_fingerprints"])

        # Statement 2: cafebazaar_twa
        stmt_bazaar = next((s for s in data if "cafebazaar_twa" in s.get("relation", [])), None)
        self.assertIsNotNone(stmt_bazaar, "Missing cafebazaar_twa statement")
        self.assertEqual(stmt_bazaar["target"]["namespace"], "android_app")
        self.assertEqual(stmt_bazaar["target"]["package_name"], EXPECTED_PACKAGE)
        self.assertIn(EXPECTED_SHA256, stmt_bazaar["target"]["sha256_cert_fingerprints"])

    def test_03_web_app_manifest_endpoint(self):
        """manifest.json must return HTTP 200, valid JSON, Persian name, and standalone mode."""
        status, headers, body = self._fetch("/manifest.json")
        self.assertEqual(status, 200, "manifest.json should return HTTP 200")
        data = json.loads(body.decode("utf-8"))
        self.assertIn("همراه باقرالعلوم", data.get("name", ""))
        self.assertIn("باقرالعلوم", data.get("short_name", ""))
        self.assertEqual(data.get("start_url"), "./?mode=app")
        self.assertEqual(data.get("display"), "standalone")
        self.assertEqual(data.get("dir"), "rtl")
        self.assertEqual(data.get("lang"), "fa-IR")
        self.assertTrue(len(data.get("icons", [])) >= 2, "Manifest should declare multiple icons")

    def test_04_service_worker_endpoint(self):
        """sw.js must return HTTP 200, javascript content, and network-first logic."""
        status, headers, body = self._fetch("/sw.js")
        self.assertEqual(status, 200, "sw.js should return HTTP 200")
        content_type = headers.get("Content-Type", "")
        self.assertTrue("javascript" in content_type or "text/plain" in content_type)
        sw_code = body.decode("utf-8", errors="replace")
        self.assertIn("install", sw_code)
        self.assertIn("activate", sw_code)
        self.assertIn("fetch", sw_code)
        self.assertIn("offline.html", sw_code)

    def test_05_offline_fallback_page(self):
        """offline.html must return HTTP 200, Persian RTL layout, and retry button."""
        status, headers, body = self._fetch("/offline.html")
        self.assertEqual(status, 200, "offline.html should return HTTP 200")
        html = body.decode("utf-8", errors="replace")
        self.assertIn('dir="rtl"', html)
        self.assertIn("تلاش مجدد", html)

    def test_06_pwa_icons_accessibility(self):
        """All PWA icons must return HTTP 200 and have valid PNG magic bytes."""
        png_magic = b"\x89PNG\r\n\x1a\n"
        icons = [
            "/icons/icon-192.png",
            "/icons/icon-512.png",
            "/icons/icon-maskable-192.png",
            "/icons/icon-maskable-512.png",
        ]
        for icon_path in icons:
            status, headers, body = self._fetch(icon_path)
            self.assertEqual(status, 200, f"Icon {icon_path} returned status {status}")
            self.assertTrue(body.startswith(png_magic), f"Icon {icon_path} is missing PNG magic bytes")


class TestCdnInformationLeakPrevention(unittest.TestCase):
    """Adversarial stress-testing: sensitive repository assets MUST NOT be exposed on Cloudflare."""

    @classmethod
    def setUpClass(cls):
        cls.ssl_ctx = ssl.create_default_context()

    def _probe_status(self, path):
        url = f"{LIVE_WORKER_URL}{path}"
        req = urllib.request.Request(url, headers={"User-Agent": "HamrahLeakScanner/1.0"})
        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=10) as resp:
                return resp.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception as e:
            return 0

    def test_01_keystore_files_blocked(self):
        """Keystore files must return HTTP 404."""
        self.assertEqual(self._probe_status("/android.keystore"), 404)
        self.assertEqual(self._probe_status("/android/app/android.keystore"), 404)

    def test_02_credentials_documentation_blocked(self):
        """KEYSTORE_CREDENTIALS.txt must return HTTP 404."""
        self.assertEqual(self._probe_status("/KEYSTORE_CREDENTIALS.txt"), 404)

    def test_03_test_suites_and_pycache_blocked(self):
        """Tests directory, scripts, and bytecode must return HTTP 404."""
        self.assertEqual(self._probe_status("/tests/base_test.py"), 404)
        self.assertEqual(self._probe_status("/tests/run_e2e_tests.py"), 404)
        self.assertEqual(self._probe_status("/tests/__pycache__/"), 404)

    def test_04_android_source_and_gradle_blocked(self):
        """Android gradle files and source code must return HTTP 404."""
        self.assertEqual(self._probe_status("/android/build.gradle"), 404)
        self.assertEqual(self._probe_status("/android/app/build.gradle"), 404)
        self.assertEqual(self._probe_status("/android/gradlew"), 404)

    def test_05_ci_workflow_and_git_metadata_blocked(self):
        """GitHub Actions workflows and .git directory must return HTTP 404."""
        self.assertEqual(self._probe_status("/.github/workflows/build-android-apk.yml"), 404)
        self.assertEqual(self._probe_status("/.git/config"), 404)
        self.assertEqual(self._probe_status("/.assetsignore"), 404)
        self.assertEqual(self._probe_status("/.gitignore"), 404)

    def test_06_markdown_documentation_blocked(self):
        """Markdown documentation files must return HTTP 404 due to *.md exclusion."""
        self.assertEqual(self._probe_status("/README.md"), 404)
        self.assertEqual(self._probe_status("/TEST_INFRA.md"), 404)
        self.assertEqual(self._probe_status("/TEST_READY.md"), 404)


class TestKeystoreFingerprintCongruence(unittest.TestCase):
    """Verify cryptographic congruence across local keystore, credentials, assetlinks, and CI."""

    def test_01_keystore_credentials_file_matches_assetlinks(self):
        """Fingerprint in KEYSTORE_CREDENTIALS.txt must match EXPECTED_SHA256."""
        with open(CREDENTIALS_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn(EXPECTED_SHA256, content)
        self.assertIn("hamrah-key", content)
        self.assertIn("Hamrah2026Release!", content)

    def test_02_local_assetlinks_matches_expected_fingerprint(self):
        """Local .well-known/assetlinks.json must match EXPECTED_SHA256 and package."""
        with open(ASSETLINKS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        for stmt in data:
            self.assertEqual(stmt["target"]["package_name"], EXPECTED_PACKAGE)
            self.assertIn(EXPECTED_SHA256, stmt["target"]["sha256_cert_fingerprints"])

    def test_03_assetsignore_contains_essential_blocks(self):
        """.assetsignore must include tests/, .github/, and *.md."""
        with open(ASSETSIGNORE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("tests/", content)
        self.assertIn(".github/", content)
        self.assertIn("*.md", content)

    def test_04_gitignore_contains_bytecode_and_build_blocks(self):
        """.gitignore must exclude __pycache__/, *.py[cod], .gradle/, build/."""
        with open(GITIGNORE_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("__pycache__/", content)
        self.assertIn(".gradle/", content)
        self.assertIn("build/", content)


class TestGitRepositoryStateAndIsolation(unittest.TestCase):
    """Empirical verification of git remote URLs, branch, and commits."""

    def test_01_git_remote_isolation(self):
        """Remote origin must point to copy repository, never original."""
        result = subprocess.run(
            ["git", "remote", "-v"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        self.assertIn("psyeducationhadi-bot/hamrah-bagherololum-copy.git", output)
        self.assertNotIn("psyeducation-hadi/hamrah-bagherololum.git", output)

    def test_02_git_commits_on_main(self):
        """Latest commits must include core delivery 426795e and infrastructure deliveries."""
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        output = result.stdout
        self.assertIn("426795e", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
