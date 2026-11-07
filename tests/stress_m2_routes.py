#!/usr/bin/env python3
"""Milestone 2 Route Guards and Web Mode Preservation Adversarial Stress Harness.

Empirical verification suite executing in a real headless Chrome/Edge browser via
Chrome DevTools Protocol (CDP) with persistent WebSocket connection.

Stress-tests:
1. Deep Linking Bypass Attempts (#admin, #/admin, #/admin/dashboard, index.html#admin?mode=app)
2. Programmatic Bypass Attempts (navigateTo('admin'), openStaffLoginModal(), renderAdminView(), DOM injection)
3. State Transitions (App mode ?mode=app -> Web mode reset ?mode=web -> Standard web persistence)
4. Student Flow Isolation (AuthService.updateHeaderBadges with student auth, logout, navigation)
5. Anti-FOUC CSS Shield Resilience (Computed style inspection for admin triggers)
"""

import asyncio
import functools
import http.server
import json
import os
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

# Ensure UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import requests
import websockets

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def find_browser_executable():
    """Locate Chrome or Edge executable on the host system."""
    candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    raise RuntimeError("No suitable Chrome or Edge browser executable found.")


def get_free_port():
    """Find an available TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class LocalHttpServer:
    """Threaded HTTP server serving the project root directory."""

    def __init__(self, directory=PROJECT_ROOT):
        self.port = get_free_port()
        self.directory = str(directory)
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=self.directory)
        self.httpd = socketserver.TCPServer(("127.0.0.1", self.port), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def base_url(self):
        return f"http://127.0.0.1:{self.port}"


class PersistentCDPClient:
    """Manages persistent WebSocket connection to Chrome DevTools Protocol."""

    def __init__(self, base_url):
        self.base_url = base_url
        self.browser_exe = find_browser_executable()
        self.cdp_port = get_free_port()
        self.tmp_dir = tempfile.mkdtemp(prefix="hamrah_cdp_")
        self.proc = None
        self.ws = None
        self._id = 0

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start(self):
        cmd = [
            self.browser_exe,
            "--headless=new",
            f"--remote-debugging-port={self.cdp_port}",
            f"--user-data-dir={self.tmp_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-translate",
            "about:blank",
        ]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Wait for CDP endpoint to respond
        ws_url = None
        for _ in range(40):
            try:
                resp = requests.get(f"http://127.0.0.1:{self.cdp_port}/json", timeout=1)
                tabs = resp.json()
                if tabs and "webSocketDebuggerUrl" in tabs[0]:
                    ws_url = tabs[0]["webSocketDebuggerUrl"]
                    break
            except Exception:
                pass
            time.sleep(0.1)
        if not ws_url:
            raise RuntimeError(f"Failed to connect to CDP on port {self.cdp_port}")

        async def _connect():
            self.ws = await websockets.connect(ws_url, max_size=16 * 1024 * 1024)
        asyncio.run_coroutine_threadsafe(_connect(), self.loop).result(timeout=6)

    def stop(self):
        async def _disconnect():
            if self.ws:
                await self.ws.close()
        try:
            asyncio.run_coroutine_threadsafe(_disconnect(), self.loop).result(timeout=2)
        except Exception:
            pass
        self.loop.call_soon_threadsafe(self.loop.stop)
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=3)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def send_cmd(self, method, params=None, timeout=8):
        self._id += 1
        msg_id = self._id
        cmd = {"id": msg_id, "method": method, "params": params or {}}

        async def _send():
            await self.ws.send(json.dumps(cmd))
            while True:
                raw = await self.ws.recv()
                data = json.loads(raw)
                if data.get("id") == msg_id:
                    return data
        return asyncio.run_coroutine_threadsafe(_send(), self.loop).result(timeout=timeout)

    def eval_js(self, expression, timeout=8):
        """Evaluate JavaScript in page and return result value."""
        res = self.send_cmd("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True
        }, timeout=timeout)
        result = res.get("result", {}).get("result", {})
        if "value" in result:
            return result["value"]
        if result.get("subtype") == "error":
            raise RuntimeError(f"JS Error: {result.get('description')}")
        return result

    def navigate(self, relative_path, wait_ready=True, timeout=12):
        """Navigate to URL and wait for page initialization."""
        url = f"{self.base_url}/{relative_path.lstrip('/')}"
        self.send_cmd("Page.navigate", {"url": url}, timeout=timeout)
        if wait_ready:
            self.wait_for_condition(
                "document.readyState === 'complete' && typeof STATE !== 'undefined' && STATE.currentView",
                timeout=timeout
            )

    def wait_for_condition(self, condition_js, timeout=12, interval=0.05):
        """Poll JavaScript condition until it returns truthy."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                val = self.eval_js(f"Boolean({condition_js})")
                if val:
                    return True
            except Exception:
                pass
            time.sleep(interval)
        val = self.eval_js(f"Boolean({condition_js})")
        if not val:
            raise TimeoutError(f"Condition '{condition_js}' not met within {timeout}s")
        return True

    def reset_storage(self):
        """Reset localStorage, sessionStorage, and clear hash."""
        try:
            self.eval_js("""
                try {
                    localStorage.clear();
                    sessionStorage.clear();
                } catch(e) {}
            """)
        except Exception:
            pass


class TestStressM2Routes(unittest.TestCase):
    """Adversarial stress tests for Milestone 2 in a real browser engine."""

    @classmethod
    def setUpClass(cls):
        cls.server = LocalHttpServer()
        cls.server.start()
        cls.browser = PersistentCDPClient(cls.server.base_url)
        cls.browser.start()
        # Cold start warmup to cache CDN resources (Tailwind, fonts)
        cls.browser.navigate("index.html", timeout=15)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.browser.stop()
        finally:
            cls.server.stop()

    def setUp(self):
        # Reset storage and cookies before each test
        self.browser.reset_storage()

    # =========================================================================
    # Suite 1: Deep Linking Bypass Attempts
    # =========================================================================

    def test_01_deeplink_hash_admin_in_app_mode(self):
        """Adversarial: Deep linking to ?mode=app#admin must redirect to #/home and view 'home'."""
        self.browser.navigate("index.html?mode=app#admin")
        state = self.browser.eval_js("""
            ({
                currentView: STATE.currentView,
                hash: window.location.hash,
                isApp: window.__HAMRAH_IS_APP_MODE,
                hasMobileClass: document.documentElement.classList.contains('is-mobile-app'),
                adminBtn: Boolean(document.getElementById('header-admin-btn'))
            })
        """)
        self.assertTrue(state["isApp"], "window.__HAMRAH_IS_APP_MODE must be true in app mode")
        self.assertTrue(state["hasMobileClass"], "<html> must have class 'is-mobile-app'")
        self.assertEqual(state["currentView"], "home", "STATE.currentView must redirect to 'home'")
        self.assertEqual(state["hash"], "#/home", "Hash must be rewritten to '#/home'")
        self.assertFalse(state["adminBtn"], "#header-admin-btn must be removed from DOM")

    def test_02_deeplink_hash_slash_admin_in_app_mode(self):
        """Adversarial: Deep linking to ?mode=app#/admin must redirect to #/home."""
        self.browser.navigate("index.html?mode=app#/admin")
        state = self.browser.eval_js("""
            ({
                currentView: STATE.currentView,
                hash: window.location.hash,
                adminBtn: Boolean(document.getElementById('header-admin-btn'))
            })
        """)
        self.assertEqual(state["currentView"], "home")
        self.assertEqual(state["hash"], "#/home")
        self.assertFalse(state["adminBtn"])

    def test_03_deeplink_admin_nested_subroutes_in_app_mode(self):
        """Adversarial: Deep linking to ?mode=app#/admin/dashboard, users, or editor must redirect to #/home."""
        for subroute in ["#/admin/dashboard", "#/admin/users", "#/admin/editor", "#/admin/approvals"]:
            self.browser.navigate(f"index.html?mode=app{subroute}")
            state = self.browser.eval_js("({ currentView: STATE.currentView, hash: window.location.hash })")
            self.assertEqual(
                state["currentView"],
                "home",
                f"Subroute {subroute} in app mode must redirect to 'home', got {state['currentView']}"
            )
            self.assertEqual(
                state["hash"],
                "#/home",
                f"Subroute {subroute} hash must be normalized to '#/home'"
            )

    def test_04_runtime_hashchange_tampering_in_app_mode(self):
        """Adversarial: Setting window.location.hash to #admin at runtime in app mode must be caught."""
        self.browser.navigate("index.html?mode=app")
        # Attacker attempts to change hash via script or address bar
        self.browser.eval_js("window.location.hash = '#admin';")
        self.browser.wait_for_condition("window.location.hash === '#/home' && STATE.currentView === 'home'")

        # Second attempt with nested admin route
        self.browser.eval_js("window.location.hash = '#/admin/users';")
        self.browser.wait_for_condition("window.location.hash === '#/home' && STATE.currentView === 'home'")

        admin_rendered = self.browser.eval_js("Boolean(document.getElementById('admin-cms-root'))")
        self.assertFalse(admin_rendered, "Admin CMS DOM elements must not be rendered")

    def test_05_deeplink_hash_admin_with_query_param_index_html_hash_admin_mode_app(self):
        """Adversarial: URL format 'index.html#admin?mode=app' (query placed after hash fragment).

        Tests whether placing mode=app inside or after the fragment causes security leakage.
        Expected: Admin panel is NOT accessible; route safely resolves to home or 404.
        """
        self.browser.navigate("index.html#admin?mode=app")
        state = self.browser.eval_js("""
            ({
                currentView: STATE.currentView,
                hash: window.location.hash,
                isStaff: AuthService.isAuthenticatedStaff(),
                adminCmsPresent: Boolean(document.getElementById('admin-cms-root') || document.querySelector('.admin-dashboard-container'))
            })
        """)
        self.assertFalse(state["isStaff"], "Unauthenticated user must not be staff")
        self.assertFalse(state["adminCmsPresent"], "Admin CMS must never render for unauthenticated requests")
        self.assertIn(
            state["currentView"],
            ["home", "404"],
            f"Adversarial route '#admin?mode=app' must safely resolve to home or 404, got {state['currentView']}"
        )

    def test_06_unauthenticated_web_mode_hash_admin_intercepted(self):
        """Web baseline: Accessing #/admin in standard web mode without authentication must block CMS."""
        self.browser.navigate("index.html#/admin")
        state = self.browser.eval_js("""
            (() => {
                const backdrop = document.getElementById('global-modal-backdrop');
                return {
                    currentView: STATE.currentView,
                    modalVisible: Boolean(backdrop && !backdrop.classList.contains('hidden')),
                    hasLoginForm: Boolean(document.getElementById('auth-username-inp')),
                    adminCmsPresent: Boolean(document.getElementById('admin-cms-root'))
                };
            })()
        """)
        self.assertFalse(state["adminCmsPresent"], "Admin CMS must not be rendered without staff auth")
        self.assertTrue(state["modalVisible"], "Staff login modal must be presented to unauthenticated user")
        self.assertTrue(state["hasLoginForm"], "Staff login modal must contain username input")

    # =========================================================================
    # Suite 2: Programmatic Bypass Attempts
    # =========================================================================

    def test_07_programmatic_navigateTo_admin_blocked_in_app_mode(self):
        """Adversarial: Calling navigateTo('admin') from JavaScript console in app mode must fail safely."""
        self.browser.navigate("index.html?mode=app")
        result = self.browser.eval_js("""
            (() => {
                navigateTo('admin');
                return {
                    currentView: STATE.currentView,
                    hash: window.location.hash,
                    adminAuditLogsCount: (DB.adminAuditLogs || []).length
                };
            })()
        """)
        self.assertEqual(result["currentView"], "home", "navigateTo('admin') in app mode must redirect to 'home'")
        self.assertEqual(result["hash"], "#/home")
        # Verify security audit log entry was created
        log_entry_match = self.browser.eval_js("""
            (DB.adminAuditLogs || []).some(log => log.action && log.action.includes('پنل مدیریت در حالت اپلیکیشن'))
        """)
        self.assertTrue(log_entry_match, "Security event must be logged to DB.adminAuditLogs")

    def test_08_programmatic_openStaffLoginModal_blocked_in_app_mode(self):
        """Adversarial: Calling openStaffLoginModal() in app mode must NOT display the login modal."""
        self.browser.navigate("index.html?mode=app")
        modal_state = self.browser.eval_js("""
            (() => {
                openStaffLoginModal();
                const backdrop = document.getElementById('global-modal-backdrop');
                const isHidden = !backdrop || backdrop.classList.contains('hidden');
                const hasInp = Boolean(document.getElementById('auth-username-inp'));
                return { isHidden, hasInp };
            })()
        """)
        self.assertTrue(modal_state["isHidden"], "Modal container must remain hidden")
        self.assertFalse(modal_state["hasInp"], "Login input elements must not be injected")

    def test_09_programmatic_renderAdminView_fallback_in_app_mode(self):
        """Adversarial: Direct execution of renderAdminView() in app mode must return home view."""
        self.browser.navigate("index.html?mode=app")
        html_output = self.browser.eval_js("renderAdminView();")
        self.assertNotIn("داشبورد آماری", html_output, "renderAdminView must not return admin dashboard")
        self.assertNotIn("admin-cms-root", html_output)

    def test_10_adversarial_dom_re_injection_caught_by_observer_and_shield(self):
        """Adversarial: Dynamic DOM re-injection of admin buttons in app mode must be destroyed."""
        self.browser.navigate("index.html?mode=app")
        self.browser.eval_js("""
            (() => {
                const btn = document.createElement('button');
                btn.id = 'header-admin-btn';
                btn.setAttribute('data-admin-trigger', 'true');
                btn.className = 'admin-panel-trigger test-injected';
                btn.textContent = 'نفوذ به مدیریت';
                document.body.appendChild(btn);
            })()
        """)
        # Wait a short tick for MutationObserver
        time.sleep(0.08)
        dom_status = self.browser.eval_js("""
            (() => {
                const btn = document.getElementById('header-admin-btn');
                const triggers = document.querySelectorAll('.test-injected');
                return {
                    btnExists: Boolean(btn),
                    triggerCount: triggers.length
                };
            })()
        """)
        self.assertFalse(dom_status["btnExists"], "MutationObserver must remove re-injected admin button")
        self.assertEqual(dom_status["triggerCount"], 0)

    # =========================================================================
    # Suite 3: State Transitions (App Mode -> Web Mode Reset)
    # =========================================================================

    def test_11_state_transition_app_to_web_reset(self):
        """State Transition: ?mode=app sets flag; visiting ?mode=web clears flag and restores UI."""
        # Step 1: App Mode active
        self.browser.navigate("index.html?mode=app")
        app_state = self.browser.eval_js("""
            ({
                storage: localStorage.getItem('HAMRAH_APP_MODE'),
                hasMobileClass: document.documentElement.classList.contains('is-mobile-app'),
                isAppGlobal: window.__HAMRAH_IS_APP_MODE,
                adminBtn: Boolean(document.getElementById('header-admin-btn'))
            })
        """)
        self.assertEqual(app_state["storage"], "1")
        self.assertTrue(app_state["hasMobileClass"])
        self.assertTrue(app_state["isAppGlobal"])
        self.assertFalse(app_state["adminBtn"])

        # Step 2: Web Mode reset (?mode=web)
        self.browser.navigate("index.html?mode=web")
        web_state = self.browser.eval_js("""
            ({
                storage: localStorage.getItem('HAMRAH_APP_MODE'),
                hasMobileClass: document.documentElement.classList.contains('is-mobile-app'),
                isAppGlobal: window.__HAMRAH_IS_APP_MODE,
                adminBtn: Boolean(document.getElementById('header-admin-btn'))
            })
        """)
        self.assertIsNone(web_state["storage"], "localStorage 'HAMRAH_APP_MODE' must be deleted by ?mode=web")
        self.assertFalse(web_state["hasMobileClass"], "'is-mobile-app' class must be removed from <html>")
        self.assertFalse(web_state["isAppGlobal"], "window.__HAMRAH_IS_APP_MODE must be false")
        self.assertTrue(web_state["adminBtn"], "#header-admin-btn must be present and visible in web mode")

        # Step 3: Admin button is functional in Web Mode
        modal_opened = self.browser.eval_js("""
            (() => {
                const btn = document.getElementById('header-admin-btn');
                if (btn) btn.click();
                const backdrop = document.getElementById('global-modal-backdrop');
                return Boolean(backdrop && !backdrop.classList.contains('hidden') && document.getElementById('auth-username-inp'));
            })()
        """)
        self.assertTrue(modal_opened, "Clicking admin button in web mode must open staff login modal")

    def test_12_web_mode_persists_after_reset(self):
        """State Transition: After ?mode=web, subsequent visits to index.html stay in Web Mode."""
        self.browser.navigate("index.html?mode=app")
        self.browser.navigate("index.html?mode=web")
        self.browser.navigate("index.html")
        state = self.browser.eval_js("""
            ({
                storage: localStorage.getItem('HAMRAH_APP_MODE'),
                hasMobileClass: document.documentElement.classList.contains('is-mobile-app'),
                adminBtn: Boolean(document.getElementById('header-admin-btn'))
            })
        """)
        self.assertIsNone(state["storage"])
        self.assertFalse(state["hasMobileClass"])
        self.assertTrue(state["adminBtn"], "Admin button must remain present in baseline web mode")

    # =========================================================================
    # Suite 4: Student Flow Isolation
    # =========================================================================

    def test_13_student_auth_does_not_resurrect_admin_button_in_app_mode(self):
        """Student Isolation: Student auth via AuthService.updateHeaderBadges updates name without admin leak."""
        self.browser.navigate("index.html?mode=app")

        # Initial baseline label
        initial_label = self.browser.eval_js("document.getElementById('header-user-label').textContent.trim();")
        self.assertEqual(initial_label, "پنل دانش‌آموز")

        # Simulate student login
        result = self.browser.eval_js("""
            (() => {
                STATE.currentUser = {
                    id: 'u_student_test_1',
                    name: 'محمد صادقی',
                    username: 'sadeghi_m',
                    roleId: 'role-student',
                    roleLabel: 'دانش‌آموز',
                    isGuest: false
                };
                AuthService.updateHeaderBadges();
                return {
                    label: document.getElementById('header-user-label').textContent.trim(),
                    adminBtn: Boolean(document.getElementById('header-admin-btn')),
                    triggersCount: document.querySelectorAll('[data-admin-trigger]').length
                };
            })()
        """)
        self.assertEqual(result["label"], "محمد صادقی", "Student name badge must update to authenticated student")
        self.assertFalse(result["adminBtn"], "Admin button must NOT be re-created in app mode upon student login")
        self.assertEqual(result["triggersCount"], 0, "No admin triggers must exist in app mode")

    def test_14_student_logout_in_app_mode_preserves_isolation(self):
        """Student Isolation: Student logout reverts user label to Persian default without admin leak."""
        self.browser.navigate("index.html?mode=app")
        # Login student then logout
        result = self.browser.eval_js("""
            (() => {
                STATE.currentUser = { id: 'u_s1', name: 'علی حسینی', roleId: 'role-student', isGuest: false };
                AuthService.updateHeaderBadges();
                // Logout
                STATE.currentUser = null;
                AuthService.updateHeaderBadges();
                return {
                    label: document.getElementById('header-user-label').textContent.trim(),
                    adminBtn: Boolean(document.getElementById('header-admin-btn'))
                };
            })()
        """)
        self.assertEqual(result["label"], "پنل دانش‌آموز")
        self.assertFalse(result["adminBtn"])

    def test_15_student_full_navigation_lifecycle_in_app_mode(self):
        """Student Isolation: Navigating between quizzes, faq, tools, categories never leaks admin UI."""
        self.browser.navigate("index.html?mode=app")
        views_to_test = ["quizzes", "faq", "tools", "categories", "majors", "explorer"]
        for v in views_to_test:
            self.browser.eval_js(f"navigateTo('{v}');")
            self.browser.wait_for_condition(f"STATE.currentView === '{v}'")
            state = self.browser.eval_js("""
                ({
                    adminBtn: Boolean(document.getElementById('header-admin-btn')),
                    triggers: document.querySelectorAll('[data-admin-trigger], .admin-panel-trigger').length
                })
            """)
            self.assertFalse(state["adminBtn"], f"Admin button leaked in view '{v}'")
            self.assertEqual(state["triggers"], 0, f"Admin triggers found in view '{v}'")

    # =========================================================================
    # Suite 5: Anti-FOUC CSS Shield Resilience
    # =========================================================================

    def test_16_anti_fouc_css_rules_guarantee_display_none(self):
        """Anti-FOUC: Rules under .is-mobile-app enforce display: none !important and visibility: hidden."""
        self.browser.navigate("index.html?mode=app")
        styles = self.browser.eval_js("""
            (() => {
                const shieldStyle = document.getElementById('app-mode-shield');
                const cssText = shieldStyle ? shieldStyle.textContent : '';
                return {
                    hasShieldTag: Boolean(shieldStyle),
                    hasDisplayNone: cssText.includes('display: none !important'),
                    hasVisibilityHidden: cssText.includes('visibility: hidden !important'),
                    hasPointerEventsNone: cssText.includes('pointer-events: none !important')
                };
            })()
        """)
        self.assertTrue(styles["hasShieldTag"], "<style id='app-mode-shield'> must be present in <head>")
        self.assertTrue(styles["hasDisplayNone"], "Shield must include display: none !important")
        self.assertTrue(styles["hasVisibilityHidden"], "Shield must include visibility: hidden !important")
        self.assertTrue(styles["hasPointerEventsNone"], "Shield must include pointer-events: none !important")

    # =========================================================================
    # Suite 6: Additional Adversarial Signals & Edge Cases
    # =========================================================================

    def test_17_source_twa_parameter_activates_app_mode(self):
        """Signal: ?source=twa activates app mode without ?mode=app parameter."""
        self.browser.navigate("index.html?source=twa")
        state = self.browser.eval_js("""
            ({
                isApp: window.__HAMRAH_IS_APP_MODE,
                hasMobileClass: document.documentElement.classList.contains('is-mobile-app'),
                storage: localStorage.getItem('HAMRAH_APP_MODE'),
                adminBtn: Boolean(document.getElementById('header-admin-btn'))
            })
        """)
        self.assertTrue(state["isApp"])
        self.assertTrue(state["hasMobileClass"])
        self.assertEqual(state["storage"], "1")
        self.assertFalse(state["adminBtn"])

    def test_18_arbitrary_mode_parameters_do_not_activate_app_mode(self):
        """Edge: Parameters like ?mode=unknown do NOT trigger app mode (baseline web preserved)."""
        self.browser.navigate("index.html?mode=unknown")
        state = self.browser.eval_js("""
            ({
                isApp: window.__HAMRAH_IS_APP_MODE,
                hasMobileClass: document.documentElement.classList.contains('is-mobile-app'),
                storage: localStorage.getItem('HAMRAH_APP_MODE'),
                adminBtn: Boolean(document.getElementById('header-admin-btn'))
            })
        """)
        self.assertFalse(state["isApp"], "?mode=unknown must not activate app mode")
        self.assertFalse(state["hasMobileClass"], "<html> must not have class is-mobile-app")
        self.assertIsNone(state["storage"], "localStorage HAMRAH_APP_MODE must not be set")
        self.assertTrue(state["adminBtn"], "Admin button must remain present for ?mode=unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)
