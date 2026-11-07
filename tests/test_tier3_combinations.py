"""Tier 3: Cross-Feature Integration & Contract Verification Tests.

Validates end-to-end interface contracts across milestones:
- M1 (Keystore / DAL) <-> M4 (Android TWA) certificate fingerprint & package ID parity
- M2 (App Mode Guard) <-> M4 (TWA DEFAULT_URL) launch parameter congruence
- M3 (PWA Manifest) <-> Filesystem icons parity
- M3 (Service Worker) <-> Offline Fallback pre-cache file integrity
- M1 (GitHub Pages) <-> M4 (ADDITIONAL_TRUSTED_ORIGINS) multi-origin fallback contract
- M1 (Brand) <-> M3 (Manifest) <-> M4 (Android) Persian name uniformity
"""

import json
import re
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from base_test import BaseE2ETest, PROJECT_ROOT


class TestTier3Combinations(BaseE2ETest):
    @classmethod
    def setUpClass(cls):
        cls.android_gradle_path = cls.android_dir / "app" / "build.gradle"
        cls.android_manifest_path = cls.android_dir / "app" / "src" / "main" / "AndroidManifest.xml"
        cls.android_arrays_path = cls.android_dir / "app" / "src" / "main" / "res" / "values" / "arrays.xml"
        cls.android_strings_path = cls.android_dir / "app" / "src" / "main" / "res" / "values" / "strings.xml"

    # -------------------------------------------------------------------------
    # Combination 1: Keystore Fingerprint <-> Assetlinks <-> Android Package ID
    # -------------------------------------------------------------------------
    def test_combo_keystore_assetlinks_package_congruence(self):
        """Combo: SHA-256 fingerprint in KEYSTORE_CREDENTIALS matches assetlinks.json & package ID."""
        self.assertTrue(
            self.assetlinks_path.exists(),
            "assetlinks.json must exist to verify certificate contract",
        )
        self.assertTrue(
            self.keystore_txt_path.exists(),
            "KEYSTORE_CREDENTIALS.txt must exist to verify certificate contract",
        )

        txt_content = self.keystore_txt_path.read_text(encoding="utf-8")
        fp_match = re.search(r"([0-9A-Fa-f]{2}:){31}[0-9A-Fa-f]{2}", txt_content)
        self.assertIsNotNone(fp_match, "Could not find SHA-256 fingerprint in KEYSTORE_CREDENTIALS.txt")
        expected_fp = fp_match.group(0).upper()

        assetlinks_data = json.loads(self.assetlinks_path.read_text(encoding="utf-8"))
        for stmt in assetlinks_data:
            target = stmt.get("target", {})
            self.assertEqual(
                target.get("package_name"),
                "ir.bagherololum.hamrah",
                "Package name across all assetlinks statements must be 'ir.bagherololum.hamrah'",
            )
            fps = target.get("sha256_cert_fingerprints", [])
            self.assertIn(
                expected_fp,
                fps,
                f"assetlinks.json must include keystore SHA-256 fingerprint '{expected_fp}'",
            )

        if self.android_gradle_path.exists():
            gradle_text = self.android_gradle_path.read_text(encoding="utf-8")
            self.assertIn(
                'applicationId "ir.bagherololum.hamrah"',
                gradle_text,
                "android/app/build.gradle applicationId must match assetlinks package_name",
            )

    # -------------------------------------------------------------------------
    # Combination 2: Android DEFAULT_URL <-> App Mode Inline Guard in index.html
    # -------------------------------------------------------------------------
    def test_combo_android_default_url_triggers_index_app_mode(self):
        """Combo: Android DEFAULT_URL query param matches index.html app-mode guard."""
        if not self.android_manifest_path.exists():
            self.skipTest("AndroidManifest.xml not yet created (M4 pending)")

        manifest_text = self.android_manifest_path.read_text(encoding="utf-8")
        url_match = re.search(
            r'android:name="android\.support\.customtabs\.trusted\.DEFAULT_URL"\s+android:value="([^"]+)"',
            manifest_text,
        )
        self.assertIsNotNone(url_match, "DEFAULT_URL meta-data must be present in AndroidManifest.xml")
        default_url = url_match.group(1)

        parsed = urlparse(default_url)
        params = parse_qs(parsed.query)

        has_app_mode_param = ("mode" in params and "app" in params["mode"]) or (
            "source" in params and "twa" in params["source"]
        )
        self.assertTrue(
            has_app_mode_param,
            f"Android DEFAULT_URL ('{default_url}') must include mode=app or source=twa",
        )

        index_content = self.index_path.read_text(encoding="utf-8")
        self.assert_in_text(
            "is-mobile-app",
            index_content,
            "index.html must apply 'is-mobile-app' when receiving DEFAULT_URL parameters",
        )

    # -------------------------------------------------------------------------
    # Combination 3: Manifest Icons Declaration <-> Physical PNG Files
    # -------------------------------------------------------------------------
    def test_combo_manifest_icons_exist_on_filesystem(self):
        """Combo: Every icon declared in manifest.json must physically exist and match specs."""
        self.assertTrue(self.manifest_path.exists(), "manifest.json must exist")
        manifest_data = json.loads(self.manifest_path.read_text(encoding="utf-8"))

        icons = manifest_data.get("icons", [])
        self.assertGreater(len(icons), 0, "manifest.json must declare icons")

        for icon in icons:
            src = icon.get("src", "")
            if not src.startswith("data:"):
                clean_src = src.lstrip("./")
                icon_file = self.root / clean_src
                self.assertTrue(
                    icon_file.exists(),
                    f"Manifest icon '{src}' was not found at '{icon_file}'",
                )
                self.assertGreater(
                    icon_file.stat().st_size,
                    100,
                    f"Icon '{src}' file size must be non-trivial (>100 bytes)",
                )

    # -------------------------------------------------------------------------
    # Combination 4: Service Worker Cache <-> Pre-Cached File Integrity
    # -------------------------------------------------------------------------
    def test_combo_sw_precached_files_exist(self):
        """Combo: Files declared in sw.js pre-cache list must exist in repository root."""
        self.assertTrue(self.sw_path.exists(), "sw.js must exist")
        sw_text = self.sw_path.read_text(encoding="utf-8")

        self.assert_in_text("offline.html", sw_text, "sw.js must reference offline.html in cache list")
        self.assertTrue(self.offline_path.exists(), "offline.html must exist for sw.js pre-cache")

        cache_array_match = re.search(r"(?:STATIC_ASSETS|PRECACHE_URLS|ASSETS)\s*=\s*\[(.*?)\]", sw_text, re.DOTALL)
        if cache_array_match:
            raw_entries = re.findall(r"['\"]([^'\"]+)['\"]", cache_array_match.group(1))
            for entry in raw_entries:
                if entry in ("./", "/", "") or entry.startswith("http"):
                    continue
                clean_entry = entry.lstrip("./")
                target_path = self.root / clean_entry
                self.assertTrue(
                    target_path.exists(),
                    f"Asset '{entry}' in sw.js pre-cache list does not exist at '{target_path}'",
                )

    # -------------------------------------------------------------------------
    # Combination 5: Multi-Origin Fallback Contract
    # -------------------------------------------------------------------------
    def test_combo_multiorigin_fallback_pages_and_nojekyll(self):
        """Combo: Fallback origin in Android arrays matches GitHub Pages URL and .nojekyll."""
        self.assertTrue(
            self.nojekyll_path.exists(),
            ".nojekyll must exist to enable GitHub Pages fallback domain to serve assetlinks",
        )

        if self.android_arrays_path.exists():
            arrays_text = self.android_arrays_path.read_text(encoding="utf-8")
            self.assertIn(
                "https://psyeducationhadi-bot.github.io",
                arrays_text,
                "additional_trusted_origins must point to https://psyeducationhadi-bot.github.io",
            )

    # -------------------------------------------------------------------------
    # Combination 6: Brand Name Uniformity Across Layers
    # -------------------------------------------------------------------------
    def test_combo_brand_name_uniformity(self):
        """Combo: Brand name 'همراه باقرالعلوم' is identical across HTML, Manifest, and Android."""
        brand = "همراه باقرالعلوم"
        self.assertIn(brand, self.index_path.read_text(encoding="utf-8"))

        if self.manifest_path.exists():
            manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            self.assertIn(brand, manifest.get("short_name", ""))

        if self.android_strings_path.exists():
            self.assertIn(brand, self.android_strings_path.read_text(encoding="utf-8"))

    # -------------------------------------------------------------------------
    # Combination 7: Keystore Credentials <-> CI/CD Workflow Script
    # -------------------------------------------------------------------------
    def test_combo_keystore_and_ci_workflow_signing(self):
        """Combo: Workflow file references keystore and credentials documented in KEYSTORE_CREDENTIALS."""
        if not self.workflow_path.exists():
            self.skipTest("Workflow build-android-apk.yml not yet created (M5 pending)")

        workflow_text = self.workflow_path.read_text(encoding="utf-8")
        creds_text = self.keystore_txt_path.read_text(encoding="utf-8") if self.keystore_txt_path.exists() else ""

        alias_match = re.search(r"(?i)alias\s*:\s*([^\r\n]+)", creds_text)
        if alias_match:
            alias = alias_match.group(1).strip()
            gradle_text = self.android_gradle_path.read_text(encoding="utf-8") if self.android_gradle_path.exists() else ""
            self.assertTrue(
                alias in workflow_text or alias in gradle_text or "KEYSTORE" in workflow_text or "SIGNING" in workflow_text,
                f"Key alias '{alias}' or signing environment variables must be referenced in CI workflow or Gradle",
            )


if __name__ == "__main__":
    unittest.main()
