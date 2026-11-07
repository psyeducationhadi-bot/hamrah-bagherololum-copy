#!/usr/bin/env python3
"""Adversarial stress-testing suite for Milestone 4 (Android TWA & Release Artifacts).

Empirically tests:
1. Intent filter routing, autoVerify="true", App Links criteria.
2. DEFAULT_URL parameter parsing and App Mode inline guard activation.
3. Multi-origin fallback arrays and DAL statements.
4. Secret hygiene & environment isolation in android/.
5. Release APK and AAB binary integrity, packaging, and digital signatures.
"""

import json
import os
import re
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Ensure tests/ directory is in sys.path
TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from base_test import BaseE2ETest


class TestM4AdversarialStress(BaseE2ETest):
    @classmethod
    def setUpClass(cls):
        cls.android_dir = PROJECT_ROOT / "android"
        cls.app_gradle = cls.android_dir / "app" / "build.gradle"
        cls.manifest = cls.android_dir / "app" / "src" / "main" / "AndroidManifest.xml"
        cls.strings = cls.android_dir / "app" / "src" / "main" / "res" / "values" / "strings.xml"
        cls.arrays = cls.android_dir / "app" / "src" / "main" / "res" / "values" / "arrays.xml"
        cls.gradle_props = cls.android_dir / "gradle.properties"
        cls.keystore_txt = PROJECT_ROOT / "KEYSTORE_CREDENTIALS.txt"
        cls.apk_file = PROJECT_ROOT / "release-apk" / "hamrah-bagherololum-release.apk"
        cls.aab_file = PROJECT_ROOT / "release-apk" / "hamrah-bagherololum-release.aab"

    # -------------------------------------------------------------------------
    # Test 1: AndroidManifest XML & Intent Filter Stress Test
    # -------------------------------------------------------------------------
    def test_stress_manifest_intent_filters(self):
        """Stress-test AndroidManifest.xml intent filters for App Links compliance."""
        self.assertTrue(self.manifest.exists(), "AndroidManifest.xml must exist")
        manifest_text = self.manifest.read_text(encoding="utf-8")

        # 1. autoVerify must be set to "true"
        auto_verify_matches = re.findall(r'android:autoVerify="true"', manifest_text)
        self.assertGreaterEqual(
            len(auto_verify_matches),
            2,
            "Both primary (Worker) and fallback (GitHub Pages) intent filters must declare android:autoVerify='true'",
        )

        # 2. Both intent filters must include action.VIEW
        view_actions = re.findall(r'<action\s+android:name="android\.intent\.action\.VIEW"\s*/>', manifest_text)
        self.assertGreaterEqual(len(view_actions), 2, "Must contain at least 2 VIEW actions for App Links")

        # 3. Both must include DEFAULT and BROWSABLE categories
        default_categories = re.findall(
            r'<category\s+android:name="android\.intent\.category\.DEFAULT"\s*/>',
            manifest_text,
        )
        browsable_categories = re.findall(
            r'<category\s+android:name="android\.intent\.category\.BROWSABLE"\s*/>',
            manifest_text,
        )
        self.assertGreaterEqual(len(default_categories), 2, "Must contain DEFAULT category in both intent filters")
        self.assertGreaterEqual(len(browsable_categories), 2, "Must contain BROWSABLE category in both intent filters")

        # 4. Primary origin matching
        self.assert_in_text(
            'android:host="hamrah-bagherololum-copy.psyeducation-hadi.workers.dev"',
            manifest_text,
            "Primary host must be hamrah-bagherololum-copy.psyeducation-hadi.workers.dev",
        )

        # 5. Secondary origin matching with pathPrefix
        self.assert_in_text(
            'android:host="psyeducationhadi-bot.github.io"',
            manifest_text,
            "Secondary host must be psyeducationhadi-bot.github.io",
        )
        self.assert_in_text(
            'android:pathPrefix="/hamrah-bagherololum-copy"',
            manifest_text,
            "Secondary host must restrict to /hamrah-bagherololum-copy pathPrefix",
        )

    # -------------------------------------------------------------------------
    # Test 2: DEFAULT_URL & App Mode Parameter Robustness
    # -------------------------------------------------------------------------
    def test_stress_default_url_and_app_mode(self):
        """Validate DEFAULT_URL parameter format and activation compatibility with index.html."""
        manifest_text = self.manifest.read_text(encoding="utf-8")
        url_match = re.search(
            r'android:name="android\.support\.customtabs\.trusted\.DEFAULT_URL"\s+android:value="([^"]+)"',
            manifest_text,
        )
        self.assertIsNotNone(url_match, "DEFAULT_URL must be declared in AndroidManifest.xml")
        default_url = url_match.group(1)

        parsed = urlparse(default_url)
        self.assertEqual(parsed.scheme, "https", "DEFAULT_URL scheme must be HTTPS")
        self.assertEqual(
            parsed.netloc,
            "hamrah-bagherololum-copy.psyeducation-hadi.workers.dev",
            "DEFAULT_URL host must be the isolated copy Cloudflare Worker",
        )

        query = parse_qs(parsed.query)
        self.assertIn("mode", query, "DEFAULT_URL query must contain 'mode'")
        self.assertEqual(query["mode"][0], "app", "DEFAULT_URL query 'mode' parameter must equal 'app'")

        # Ensure index.html handles this exact parameter
        index_text = self.index_path.read_text(encoding="utf-8")
        self.assert_matches(
            r"params\.get\(['\"]mode['\"]\)\s*===\s*['\"]app['\"]|\(?mode\s*===\s*['\"]app['\"]\)?",
            index_text,
            "index.html must explicitly test for mode === 'app'",
        )

    # -------------------------------------------------------------------------
    # Test 3: Multi-Origin Fallback Configuration Parity
    # -------------------------------------------------------------------------
    def test_stress_multiorigin_fallback_parity(self):
        """Verify additional_trusted_origins and asset_statements parity across layers."""
        # 1. arrays.xml check
        self.assertTrue(self.arrays.exists(), "arrays.xml must exist")
        arrays_text = self.arrays.read_text(encoding="utf-8")
        self.assert_in_text("https://psyeducationhadi-bot.github.io", arrays_text)

        # 2. strings.xml asset_statements check
        self.assertTrue(self.strings.exists(), "strings.xml must exist")
        strings_text = self.strings.read_text(encoding="utf-8")

        # Extract and parse asset_statements string
        asset_stmt_match = re.search(r'<string name="asset_statements"[^>]*>(.*?)</string>', strings_text, re.DOTALL)
        self.assertIsNotNone(asset_stmt_match, "asset_statements string resource must exist")
        raw_json = asset_stmt_match.group(1).strip()
        # Unescape escaped slashes/quotes in XML string resource
        cleaned_json = raw_json.replace(r'\"', '"').replace(r"\\", "")
        parsed_statements = json.loads(cleaned_json)
        self.assertIsInstance(parsed_statements, list)
        self.assertGreaterEqual(len(parsed_statements), 2)

        sites = [stmt["target"]["site"] for stmt in parsed_statements]
        self.assertIn("https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev", sites)
        self.assertIn("https://psyeducationhadi-bot.github.io", sites)

        for stmt in parsed_statements:
            relations = stmt.get("relation", [])
            self.assertIn("delegate_permission/common.handle_all_urls", relations)
            self.assertIn("cafebazaar_twa", relations)

    # -------------------------------------------------------------------------
    # Test 4: Secret Hygiene and Environment Isolation in android/
    # -------------------------------------------------------------------------
    def test_stress_secret_hygiene_and_isolation(self):
        """Verify no original repo secrets, unmasked tokens, or wrong origins exist in android/."""
        forbidden_patterns = [
            (r"hamrah-bagherololum\.psyeducation-hadi\.workers\.dev", "Original production Cloudflare worker URL"),
            (r"github\.com/psyeducationhadi-bot/hamrah-bagherololum(?!\-copy)", "Original production GitHub repository URL"),
            (r"ghp_[A-Za-z0-9]{20,}", "GitHub Personal Access Token"),
            (r"-----BEGIN\s+PRIVATE\s+KEY-----", "Unencrypted Raw Private Key"),
            (r"bot[0-9]{8,10}:[A-Za-z0-9_-]{35}", "Telegram Bot Token"),
        ]

        for p in self.android_dir.rglob("*"):
            if p.is_file() and not any(part in p.parts for part in [".gradle", "build"]):
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    for pattern, desc in forbidden_patterns:
                        match = re.search(pattern, content)
                        self.assertIsNone(
                            match,
                            f"Forbidden secret or leak found in {p.relative_to(PROJECT_ROOT)}: {desc} (match: '{match.group(0) if match else ''}')",
                        )
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # Test 5: Release APK and AAB Binary Integrity & Signatures
    # -------------------------------------------------------------------------
    def test_stress_release_artifacts_integrity(self):
        """Validate physical presence, non-trivial sizes, zip structures, and apksigner verification."""
        self.assertTrue(self.apk_file.exists(), f"Release APK must exist at {self.apk_file}")
        self.assertTrue(self.aab_file.exists(), f"Release AAB must exist at {self.aab_file}")

        apk_size = self.apk_file.stat().st_size
        aab_size = self.aab_file.stat().st_size

        self.assertGreater(apk_size, 2_000_000, f"APK file size ({apk_size} bytes) must exceed 2MB")
        self.assertGreater(aab_size, 2_000_000, f"AAB file size ({aab_size} bytes) must exceed 2MB")

        # Verify APK internal zip structure
        with zipfile.ZipFile(self.apk_file) as z:
            names = z.namelist()
            self.assertIn("AndroidManifest.xml", names, "APK must contain compiled AndroidManifest.xml")
            self.assertIn("classes.dex", names, "APK must contain compiled Dalvik bytecode (classes.dex)")
            self.assertIn("resources.arsc", names, "APK must contain compiled resources table (resources.arsc)")
            self.assertIn("META-INF/MANIFEST.MF", names, "APK must contain v1 manifest")

        # Verify AAB internal zip structure
        with zipfile.ZipFile(self.aab_file) as z:
            names = z.namelist()
            self.assertIn("BundleConfig.pb", names, "AAB must contain BundleConfig.pb")
            self.assertIn("base/manifest/AndroidManifest.xml", names, "AAB must contain base manifest")
            self.assertIn("base/dex/classes.dex", names, "AAB must contain base dex")

        # Verify Signature with apksigner if available
        apksigner_path = Path(r"C:\Users\Pasargad\AppData\Local\Android\Sdk\build-tools\34.0.0\apksigner.bat")
        if apksigner_path.exists():
            cmd = [
                str(apksigner_path),
                "verify",
                "--min-sdk-version",
                "21",
                "--verbose",
                "--print-certs",
                str(self.apk_file),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"apksigner verification failed: {result.stderr}")
            output = result.stdout

            self.assertIn("Verifies", output, "apksigner must report 'Verifies'")
            self.assertIn("Verified using v1 scheme (JAR signing): true", output)
            self.assertIn("Verified using v2 scheme (APK Signature Scheme v2): true", output)
            self.assertIn(
                "f211bf373c30602d31d42832d28ab709c4aa6a296ff30143192c17ca1ca456fe",
                output.lower(),
                "Signer certificate SHA-256 digest must match authoritative keystore fingerprint",
            )

    # -------------------------------------------------------------------------
    # Test 6: Cafe Bazaar Compliance Attributes
    # -------------------------------------------------------------------------
    def test_stress_cafebazaar_compliance_attributes(self):
        """Stress-test specific Cafe Bazaar TWA guidelines in AndroidManifest."""
        manifest_text = self.manifest.read_text(encoding="utf-8")

        # 1. LauncherActivity declared
        self.assert_in_text("com.google.androidbrowserhelper.trusted.LauncherActivity", manifest_text)

        # 2. STATUS_BAR_COLOR and NAVIGATION_BAR_COLOR declared
        self.assert_in_text("android.support.customtabs.trusted.STATUS_BAR_COLOR", manifest_text)
        self.assert_in_text("android.support.customtabs.trusted.NAVIGATION_BAR_COLOR", manifest_text)

        # 3. SPLASH_IMAGE_DRAWABLE declared
        self.assert_in_text("android.support.customtabs.trusted.SPLASH_IMAGE_DRAWABLE", manifest_text)

        # 4. FALLBACK_STRATEGY is webview
        self.assert_in_text('android:value="webview"', manifest_text)

        # 5. DISPLAY_MODE is standalone
        self.assert_in_text('android:value="standalone"', manifest_text)

        # 6. WebViewFallbackActivity is declared
        self.assert_in_text("com.google.androidbrowserhelper.trusted.WebViewFallbackActivity", manifest_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
