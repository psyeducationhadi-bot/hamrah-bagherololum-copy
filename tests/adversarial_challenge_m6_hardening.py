#!/usr/bin/env python3
"""Milestone 6 Adversarial Challenge & Comprehensive Verification Suite (Phase 2 Hardening).

Author: m6_challenger_2 (Roles: critic, specialist)
Verification Scope:
1. Cafe Bazaar & Myket TWA Guidelines Compliance:
   - Package name: ir.bagherololum.hamrah across all metadata, manifests, configs
   - Persian app title: همراه باقرالعلوم across all user-facing metadata
   - DEFAULT_URL metadata pointing to Cloudflare Worker with ?mode=app
   - Digital Asset Links: dual statements (common.handle_all_urls & cafebazaar_twa) with exact SHA-256
   - WebView fallback strategy and WebViewFallbackActivity declaration
   - Multi-origin trusted origins (Cloudflare Worker & GitHub Pages mirror)
   - Binary APK signature verification and SHA-256 fingerprint fidelity
2. Mobile UI Polish & Touch Ergonomics:
   - -webkit-tap-highlight-color: transparent on body and interactive chrome
   - user-select: none on interactive chrome with user-select: text on educational reading text
   - overflow-x: hidden and max-width: 100vw on html, body
   - Minimum readable font size: body >= 14px, input >= 16px to prevent iOS/Android zoom
   - History API Back button modal dismissal (pushState on open, popstate interception, UI close synchronization)
3. Real-Time Online Sync & Service Worker Network-First Architecture:
   - Dynamic data (db.json, /api/) and HTML navigation strictly use fetch with cache: 'no-store'
   - Dynamic data offline fallback returns JSON 503 without stale cache poisoning
   - Navigation offline fallback serves pre-cached Persian RTL offline.html
   - Static asset discrimination (png, svg, css, js, fonts) uses Cache-First
   - Pre-cached files existence and integrity
4. App Mode DOM Isolation & Security:
   - Early <head> detection script, Anti-FOUC CSS shield
   - Admin triggers removed from DOM and AuthService protected
   - Clean ?mode=web reset escape hatch
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import unittest
import urllib.request
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Core File Paths
ANDROID_DIR = PROJECT_ROOT / "android"
ANDROID_MANIFEST_PATH = ANDROID_DIR / "app" / "src" / "main" / "AndroidManifest.xml"
ANDROID_BUILD_GRADLE = ANDROID_DIR / "app" / "build.gradle"
ANDROID_STRINGS_PATH = ANDROID_DIR / "app" / "src" / "main" / "res" / "values" / "strings.xml"
ANDROID_ARRAYS_PATH = ANDROID_DIR / "app" / "src" / "main" / "res" / "values" / "arrays.xml"

KEYSTORE_PATH = PROJECT_ROOT / "android.keystore"
KEYSTORE_CREDENTIALS_PATH = PROJECT_ROOT / "KEYSTORE_CREDENTIALS.txt"
ASSETLINKS_PATH = PROJECT_ROOT / ".well-known" / "assetlinks.json"
MANIFEST_PATH = PROJECT_ROOT / "manifest.json"
INDEX_PATH = PROJECT_ROOT / "index.html"
SW_PATH = PROJECT_ROOT / "sw.js"
OFFLINE_PATH = PROJECT_ROOT / "offline.html"
RELEASE_APK_PATH = PROJECT_ROOT / "release-apk" / "hamrah-bagherololum-release.apk"
RELEASE_AAB_PATH = PROJECT_ROOT / "release-apk" / "hamrah-bagherololum-release.aab"
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "build-android-apk.yml"

# Expected Constants
EXPECTED_PACKAGE = "ir.bagherololum.hamrah"
EXPECTED_APP_TITLE = "همراه باقرالعلوم"
EXPECTED_SHA256 = "F2:11:BF:37:3C:30:60:2D:31:D4:28:32:D2:8A:B7:09:C4:AA:6A:29:6F:F3:01:43:19:2C:17:CA:1C:A4:56:FE"
EXPECTED_DEFAULT_URL = "https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/?mode=app"
EXPECTED_PAGES_FALLBACK = "https://psyeducationhadi-bot.github.io"


class TestCafeBazaarTWACompliance(unittest.TestCase):
    """Deep verification of Cafe Bazaar and Myket TWA requirements."""

    def test_01_package_name_consistency(self):
        """Package name ir.bagherololum.hamrah must be identical across all components."""
        # 1. AndroidManifest.xml
        manifest_text = ANDROID_MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertIn(f'package="{EXPECTED_PACKAGE}"', manifest_text)
        self.assertIn(f'android:authorities="{EXPECTED_PACKAGE}.fileprovider"', manifest_text)

        # 2. build.gradle
        gradle_text = ANDROID_BUILD_GRADLE.read_text(encoding="utf-8")
        self.assertIn(f'applicationId "{EXPECTED_PACKAGE}"', gradle_text)
        self.assertIn(f"namespace '{EXPECTED_PACKAGE}'", gradle_text)

        # 3. strings.xml
        strings_text = ANDROID_STRINGS_PATH.read_text(encoding="utf-8")
        self.assertIn(f'<string name="package_name" translatable="false">{EXPECTED_PACKAGE}</string>', strings_text)

        # 4. assetlinks.json
        assetlinks_data = json.loads(ASSETLINKS_PATH.read_text(encoding="utf-8"))
        for statement in assetlinks_data:
            self.assertEqual(statement["target"]["package_name"], EXPECTED_PACKAGE)

    def test_02_persian_app_title_fidelity(self):
        """Persian brand title 'همراه باقرالعلوم' must be preserved without distortion."""
        strings_text = ANDROID_STRINGS_PATH.read_text(encoding="utf-8")
        self.assertIn(f'<string name="app_name">{EXPECTED_APP_TITLE}</string>', strings_text)
        self.assertIn(f'<string name="launcher_name">{EXPECTED_APP_TITLE}</string>', strings_text)

        manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertIn(EXPECTED_APP_TITLE, manifest_data["name"])
        self.assertEqual(manifest_data["short_name"], EXPECTED_APP_TITLE)

        index_text = INDEX_PATH.read_text(encoding="utf-8")
        self.assertIn(f"<title>{EXPECTED_APP_TITLE}", index_text)
        self.assertIn(f'content="{EXPECTED_APP_TITLE}', index_text)

        offline_text = OFFLINE_PATH.read_text(encoding="utf-8")
        self.assertIn(EXPECTED_APP_TITLE, offline_text)

    def test_03_default_url_and_query_parameters(self):
        """DEFAULT_URL metadata must point to the Cloudflare Worker with ?mode=app."""
        manifest_text = ANDROID_MANIFEST_PATH.read_text(encoding="utf-8")
        match = re.search(
            r'<meta-data\s+android:name="android\.support\.customtabs\.trusted\.DEFAULT_URL"\s+android:value="([^"]+)"',
            manifest_text,
        )
        self.assertIsNotNone(match, "DEFAULT_URL meta-data tag not found in AndroidManifest.xml")
        default_url = match.group(1)
        self.assertEqual(default_url, EXPECTED_DEFAULT_URL)
        self.assertTrue(default_url.startswith("https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev"))
        self.assertTrue(default_url.endswith("?mode=app"))

    def test_04_dual_assetlinks_statements_and_sha256(self):
        """Assetlinks must declare dual relation statements with uppercase colon-separated SHA-256."""
        assetlinks_data = json.loads(ASSETLINKS_PATH.read_text(encoding="utf-8"))
        self.assertIsInstance(assetlinks_data, list)
        self.assertEqual(len(assetlinks_data), 2, "assetlinks.json must contain exactly 2 statements")

        relations = [stmt["relation"][0] for stmt in assetlinks_data]
        self.assertIn("delegate_permission/common.handle_all_urls", relations)
        self.assertIn("cafebazaar_twa", relations)

        for stmt in assetlinks_data:
            target = stmt["target"]
            self.assertEqual(target["namespace"], "android_app")
            self.assertEqual(target["package_name"], EXPECTED_PACKAGE)
            fingerprints = target["sha256_cert_fingerprints"]
            self.assertIsInstance(fingerprints, list)
            self.assertEqual(len(fingerprints), 1)
            fp = fingerprints[0]
            self.assertEqual(fp, EXPECTED_SHA256)
            self.assertEqual(fp, fp.upper(), "Fingerprint must be uppercase")
            self.assertEqual(len(fp.split(":")), 32, "Fingerprint must have 32 colon-separated hex bytes")

    def test_05_webview_fallback_strategy_configuration(self):
        """TWA must configure WebViewFallbackActivity and FALLBACK_STRATEGY=webview."""
        manifest_text = ANDROID_MANIFEST_PATH.read_text(encoding="utf-8")

        # 1. FALLBACK_STRATEGY meta-data
        fallback_match = re.search(
            r'<meta-data\s+android:name="android\.support\.customtabs\.trusted\.FALLBACK_STRATEGY"\s+android:value="([^"]+)"',
            manifest_text,
        )
        self.assertIsNotNone(fallback_match, "FALLBACK_STRATEGY metadata missing in AndroidManifest.xml")
        self.assertEqual(fallback_match.group(1), "webview")

        # 2. WebViewFallbackActivity declaration
        activity_match = re.search(
            r'<activity\s+android:name="com\.google\.androidbrowserhelper\.trusted\.WebViewFallbackActivity"[^>]*>',
            manifest_text,
        )
        self.assertIsNotNone(activity_match, "WebViewFallbackActivity not registered in AndroidManifest.xml")

    def test_06_multi_origin_trusted_fallback(self):
        """ADDITIONAL_TRUSTED_ORIGINS must include GitHub Pages mirror."""
        arrays_text = ANDROID_ARRAYS_PATH.read_text(encoding="utf-8")
        self.assertIn(EXPECTED_PAGES_FALLBACK, arrays_text)

        manifest_text = ANDROID_MANIFEST_PATH.read_text(encoding="utf-8")
        self.assertIn('android:name="android.support.customtabs.trusted.ADDITIONAL_TRUSTED_ORIGINS"', manifest_text)
        self.assertIn('android:resource="@array/additional_trusted_origins"', manifest_text)

    def test_07_binary_apk_and_aab_existence_and_signing(self):
        """hamrah-bagherololum-release.apk and .aab must exist, be valid zip archives, and signed."""
        self.assertTrue(RELEASE_APK_PATH.exists(), f"Release APK missing at {RELEASE_APK_PATH}")
        self.assertTrue(RELEASE_AAB_PATH.exists(), f"Release AAB missing at {RELEASE_AAB_PATH}")
        self.assertGreater(RELEASE_APK_PATH.stat().st_size, 1_000_000, "APK must be > 1MB")
        self.assertGreater(RELEASE_AAB_PATH.stat().st_size, 1_000_000, "AAB must be > 1MB")

        # Verify APK is a valid zip archive containing Android components
        with zipfile.ZipFile(RELEASE_APK_PATH, "r") as z:
            namelist = z.namelist()
            self.assertIn("AndroidManifest.xml", namelist)
            self.assertIn("classes.dex", namelist)
            self.assertIn("resources.arsc", namelist)

        # Verify AAB is a valid zip archive containing base module
        with zipfile.ZipFile(RELEASE_AAB_PATH, "r") as z:
            namelist = z.namelist()
            self.assertTrue(any(name.startswith("base/") for name in namelist), "AAB must contain base/ module")

        # Test signing certificate using keytool
        cmd = ["keytool", "-printcert", "-jarfile", str(RELEASE_APK_PATH)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"keytool failed on {RELEASE_APK_PATH}: {result.stderr}")
        self.assertIn(EXPECTED_SHA256, result.stdout, "APK signing SHA-256 fingerprint does not match assetlinks!")


class TestMobileTouchPolishAndErgonomics(unittest.TestCase):
    """Stress-test mobile touch polish, tap highlights, font sizes, and Back button handling."""

    def setUp(self):
        self.index_html = INDEX_PATH.read_text(encoding="utf-8")

    def test_01_tap_highlight_color_transparent(self):
        """Interactive chrome and body must enforce -webkit-tap-highlight-color: transparent."""
        self.assertIn("-webkit-tap-highlight-color: transparent", self.index_html)
        # Check rule on body
        self.assertRegex(
            self.index_html,
            r"(?:html,\s*body|body)[^{]*\{[^}]*-webkit-tap-highlight-color:\s*transparent",
        )
        # Check rule on interactive chrome
        self.assertRegex(
            self.index_html,
            r"(?:button,\s*a|interactive-element)[^{]*\{[^}]*-webkit-tap-highlight-color:\s*transparent",
        )

    def test_02_user_select_none_on_chrome_and_text_on_articles(self):
        """Chrome must have user-select: none while educational text has user-select: text."""
        # Chrome should have user-select: none
        self.assertRegex(
            self.index_html,
            r"(?:button,\s*a|interactive-element)[^{]*\{[^}]*user-select:\s*none",
        )
        self.assertRegex(
            self.index_html,
            r"(?:button,\s*a|interactive-element)[^{]*\{[^}]*-webkit-user-select:\s*none",
        )

        # Educational reading material must have user-select: text
        self.assertRegex(
            self.index_html,
            r"(?:article|selectable-text)[^{]*\{[^}]*user-select:\s*text",
        )
        self.assertRegex(
            self.index_html,
            r"(?:article|selectable-text)[^{]*\{[^}]*-webkit-user-select:\s*text",
        )

    def test_03_no_horizontal_overflow_and_safe_areas(self):
        """Layout must forbid horizontal scrolling and declare safe area padding."""
        self.assertRegex(
            self.index_html,
            r"(?:html,\s*body|body)[^{]*\{[^}]*overflow-x:\s*hidden",
        )
        self.assertRegex(
            self.index_html,
            r"(?:html,\s*body|body)[^{]*\{[^}]*max-width:\s*100vw",
        )
        self.assertIn("env(safe-area-inset-top", self.index_html)
        self.assertIn("env(safe-area-inset-bottom", self.index_html)

    def test_04_minimum_readable_font_size(self):
        """Body font size must be >= 14px and input font size >= 16px (no mobile zoom)."""
        body_font_match = re.search(r"(?:html,\s*body|body)[^{]*\{[^}]*font-size:\s*(\d+)px", self.index_html)
        self.assertIsNotNone(body_font_match)
        self.assertGreaterEqual(int(body_font_match.group(1)), 14)

        input_font_match = re.search(r"input\[type=[\"']text[\"']\][^{]*\{[^}]*font-size:\s*(\d+)px", self.index_html)
        self.assertIsNotNone(input_font_match)
        self.assertGreaterEqual(int(input_font_match.group(1)), 16)

    def test_05_history_api_popstate_modal_dismissal_mechanics(self):
        """History API popstate listener must gracefully close open modal without double-navigation."""
        # 1. Check openModal pushes history state
        self.assertRegex(
            self.index_html,
            r"function\s+openModal\s*\([^)]*\)\s*\{[\s\S]*?history\.pushState\s*\(\s*\{\s*modalOpen:\s*true",
        )

        # 2. Check window popstate event listener is registered
        self.assertRegex(
            self.index_html,
            r"window\.addEventListener\s*\(\s*['\"]popstate['\"]\s*,\s*function\s*\(\s*event\s*\)",
        )

        # 3. Check popstate listener calls closeModal(true)
        self.assertRegex(
            self.index_html,
            r"if\s*\(\s*(?:isModalOpen|isBackdropActive|event\.state)[\s\S]*?\)\s*\{\s*closeModal\s*\(\s*true\s*\);",
        )

        # 4. Check UI closeModal(false) handles _ignoreNextPopstate and history.back()
        self.assertRegex(
            self.index_html,
            r"function\s+closeModal\s*\(\s*fromPopstate\s*\)\s*\{[\s\S]*?!fromPopstate[\s\S]*?history\.back\s*\(\s*\)",
        )

        # 5. Check Escape key and backdrop click listeners exist
        self.assertIn("initModalBackdropListener", self.index_html)
        self.assertIn("e.key === 'Escape'", self.index_html)


class TestRealTimeOnlineSyncServiceWorker(unittest.TestCase):
    """Stress-test Network-First service worker cache bypass and offline fallback."""

    def setUp(self):
        self.sw_text = SW_PATH.read_text(encoding="utf-8")

    def test_01_navigation_requests_strict_network_first_no_store(self):
        """Navigation (HTML document) requests must use fetch with cache: 'no-store'."""
        self.assertRegex(
            self.sw_text,
            r"isNavigation[\s\S]*?fetch\s*\(\s*request\s*,\s*\{\s*cache:\s*['\"]no-store['\"]\s*\}\s*\)",
        )

    def test_02_dynamic_data_strict_network_first_no_store(self):
        """Dynamic CMS/API calls (db.json, /api/, workers.dev) must use cache: 'no-store'."""
        self.assertRegex(
            self.sw_text,
            r"isDynamicData[\s\S]*?fetch\s*\(\s*request\s*,\s*\{\s*cache:\s*['\"]no-store['\"]\s*\}\s*\)",
        )
        self.assertIn("db.json", self.sw_text)
        self.assertIn("/api/", self.sw_text)
        self.assertIn("workers.dev", self.sw_text)

    def test_03_dynamic_data_offline_failure_returns_json_503(self):
        """When offline, dynamic data fetch failure returns JSON 503 rather than HTML or stale data."""
        self.assertRegex(
            self.sw_text,
            r"isDynamicData[\s\S]*?\.catch[\s\S]*?JSON\.stringify\s*\(\s*\{[^}]*offline:\s*true[^}]*\}\s*\)",
        )
        self.assertRegex(
            self.sw_text,
            r"isDynamicData[\s\S]*?status:\s*503",
        )

    def test_04_navigation_offline_failure_serves_persian_offline_html(self):
        """When offline, navigation request failure serves cached offline.html or Persian 503 fallback."""
        self.assertRegex(
            self.sw_text,
            r"isNavigation[\s\S]*?\.catch[\s\S]*?cache\.match\s*\(\s*OFFLINE_URL\s*\)",
        )
        # Inline fallback must be in Persian
        self.assertIn("ارتباط با اینترنت برقرار نیست", self.sw_text)
        self.assertIn('dir="rtl"', self.sw_text)

    def test_05_static_asset_discrimination_uses_cache_first(self):
        """Static assets (images, css, js, fonts) must be discriminated and cached."""
        self.assertRegex(
            self.sw_text,
            r"isStaticAsset[\s\S]*?png|jpe?g|gif|svg|ico|webp|css|woff2?|ttf|js",
        )
        self.assertRegex(
            self.sw_text,
            r"caches\.match\s*\(\s*request\s*\)\.then\s*\(\s*\(cachedResponse\)\s*=>",
        )

    def test_06_precache_assets_exist_on_filesystem(self):
        """All assets declared in PRECACHE_URLS must physically exist."""
        # Extract PRECACHE_URLS
        match = re.search(r"const\s+PRECACHE_URLS\s*=\s*\[([\s\S]*?)\];", self.sw_text)
        self.assertIsNotNone(match, "PRECACHE_URLS array not found in sw.js")
        raw_items = match.group(1)
        urls = re.findall(r"['\"](\./[^'\"]+|[^'\"]+)['\"]", raw_items)
        self.assertGreaterEqual(len(urls), 3, "At least 3 precache URLs expected")

        for u in urls:
            clean_path = u.lstrip("./").replace("/", os.sep)
            file_path = PROJECT_ROOT / clean_path
            self.assertTrue(file_path.exists(), f"Precached asset {u} does not exist at {file_path}")
            self.assertGreater(file_path.stat().st_size, 0, f"Precached asset {u} is empty")


class TestAppModeAdminIsolationAdversarial(unittest.TestCase):
    """Adversarial stress-testing of App Mode DOM isolation and anti-FOUC."""

    def setUp(self):
        self.index_html = INDEX_PATH.read_text(encoding="utf-8")

    def test_01_early_script_in_head_before_body(self):
        """App mode detection script must appear inside <head> before any <body> content."""
        head_end = self.index_html.find("</head>")
        body_start = self.index_html.find("<body")
        script_pos = self.index_html.find("Early App Mode Detection Engine")
        self.assertNotEqual(script_pos, -1, "App Mode Detection Engine marker not found")
        self.assertLess(script_pos, head_end, "Detection engine must be in <head>")
        self.assertLess(head_end, body_start, "<head> must close before <body>")

    def test_02_anti_fouc_css_rules(self):
        """Anti-FOUC CSS shield must immediately hide admin elements under html.is-mobile-app."""
        shield_match = re.search(r'<style\s+id="app-mode-shield">([\s\S]*?)</style>', self.index_html)
        self.assertIsNotNone(shield_match, "app-mode-shield style tag not found")
        css = shield_match.group(1)
        self.assertIn("html.is-mobile-app #header-admin-btn", css)
        self.assertIn("html.is-mobile-app [data-admin-trigger]", css)
        self.assertIn("display: none !important;", css)
        self.assertIn("visibility: hidden !important;", css)

    def test_03_web_mode_escape_hatch_resets_storage_and_class(self):
        """?mode=web must remove HAMRAH_APP_MODE localStorage key and is-mobile-app class."""
        self.assertRegex(
            self.index_html,
            r"if\s*\(\s*mode\s*===\s*['\"]web['\"]\s*\)\s*\{[\s\S]*?localStorage\.removeItem\s*\(\s*['\"]HAMRAH_APP_MODE['\"]\s*\)[\s\S]*?document\.documentElement\.classList\.remove\s*\(\s*['\"]is-mobile-app['\"]\s*\)",
        )

    def test_04_auth_service_and_route_guards_purge_admin_triggers(self):
        """navigateTo('admin'), openStaffLoginModal, and AuthService must enforce app mode guards."""
        self.assertIn("__HAMRAH_IS_APP_MODE", self.index_html)
        self.assertIn("updateHeaderBadges", self.index_html)
        # Check navigateTo guard
        self.assertRegex(
            self.index_html,
            r"navigateTo\s*=\s*function\s*\(\s*view[\s\S]*?is-mobile-app[\s\S]*?view\s*===\s*['\"]admin['\"]",
        )
        # Check openStaffLoginModal guard
        self.assertRegex(
            self.index_html,
            r"(?:window\.)?openStaffLoginModal\s*=\s*function\s*\([^)]*\)\s*\{[\s\S]*?is-mobile-app",
        )


def run_tests():
    """Execute all test cases with high-verbosity reporting."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestCafeBazaarTWACompliance))
    suite.addTests(loader.loadTestsFromTestCase(TestMobileTouchPolishAndErgonomics))
    suite.addTests(loader.loadTestsFromTestCase(TestRealTimeOnlineSyncServiceWorker))
    suite.addTests(loader.loadTestsFromTestCase(TestAppModeAdminIsolationAdversarial))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
