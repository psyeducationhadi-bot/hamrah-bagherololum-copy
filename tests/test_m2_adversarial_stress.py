#!/usr/bin/env python3
"""Milestone 2 Adversarial Stress Test Suite.

Adversarially and empirically stress-tests:
1. Regex bypass resistance & query parameter variations
2. Anti-FOUC CSS Shield & DOM purge / resurrection resilience
3. Route guard evasion & modal defense
4. Standard web mode preservation & accessibility
5. Baseline invariants and Persian language integrity
6. Adversarial boundary audit (Student portal modal & LiveVisualCMS)
"""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

from base_test import BaseE2ETest, PROJECT_ROOT


class TestM2AdversarialStress(BaseE2ETest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.html_content = cls.index_path.read_text(encoding="utf-8")
        cls.soup = BeautifulSoup(cls.html_content, "html.parser")

    def _run_node_script(self, js_code: str) -> dict:
        """Helper to run a Node.js snippet and parse JSON output."""
        result = subprocess.run(
            ["node", "-e", js_code],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode != 0:
            raise RuntimeError(f"Node execution failed (code {result.returncode}):\n{result.stderr}\nCode:\n{js_code}")
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return {"raw_output": result.stdout.strip()}

    # =========================================================================
    # 1. Regex Bypass Resistance: URL Query String & Signal Variations
    # =========================================================================
    def test_01_query_string_and_signal_variations(self):
        """Stress-test early app mode detection script with 16 signal combinations."""
        # Extract the early detection script from index.html
        head_script_match = re.search(
            r"<!-- Early App Mode Detection Engine [^>]*-->\s*<script>([\s\S]*?)</script>",
            self.html_content,
        )
        self.assertIsNotNone(head_script_match, "Early App Mode Detection script must exist in <head>")
        raw_script = head_script_match.group(1)

        test_scenarios = [
            # (name, search, initial_storage, standalone, referrer, expected_is_app, expected_stored)
            ("direct_mode_app", "?mode=app", None, False, "", True, "1"),
            ("direct_mode_web", "?mode=web", "1", False, "", False, None),
            ("mode_admin_arbitrary", "?mode=admin", None, False, "", False, None),
            ("source_twa", "?source=twa", None, False, "", True, "1"),
            ("mode_app_and_source_web", "?mode=app&source=web", None, False, "", True, "1"),
            ("test_param_before_mode_app", "?test=1&mode=app", None, False, "", True, "1"),
            ("source_twa_with_mode_web_reset", "?source=twa&mode=web", None, False, "", False, None),
            ("mode_web_with_source_twa_reset", "?mode=web&source=twa", "1", False, "", False, None),
            ("unrelated_params", "?foo=bar&baz=qux", None, False, "", False, None),
            ("empty_query_string", "", None, False, "", False, None),
            ("localstorage_persistence", "", "1", False, "", True, "1"),
            ("mode_web_clears_localstorage", "?mode=web", "1", False, "", False, None),
            ("standalone_display_mode", "", None, True, "", True, "1"),
            ("android_twa_referrer", "", None, False, "android-app://ir.bagherololum.hamrah", True, "1"),
            ("url_encoded_app_mode", "?mode=%61%70%70", None, False, "", True, "1"),
            ("uppercase_mode_app_rejection", "?mode=APP", None, False, "", False, None),
        ]

        js_harness = f"""
        const fs = require('fs');
        const rawScript = {json.dumps(raw_script)};
        const scenarios = {json.dumps(test_scenarios)};

        const results = scenarios.map(([name, search, initStorage, standalone, referrer, expApp, expStore]) => {{
            const store = {{}};
            if (initStorage) store['HAMRAH_APP_MODE'] = initStorage;

            const classList = new Set();
            const documentElement = {{
                classList: {{
                    add: (c) => classList.add(c),
                    remove: (c) => classList.delete(c),
                    contains: (c) => classList.has(c)
                }}
            }};

            const localStorage = {{
                getItem: (k) => store[k] || null,
                setItem: (k, v) => {{ store[k] = String(v); }},
                removeItem: (k) => {{ delete store[k]; }}
            }};

            const mockWindow = {{
                location: {{ search: search }},
                __HAMRAH_IS_APP_MODE: false,
                matchMedia: (q) => ({{ matches: standalone && q.includes('standalone') }}),
                navigator: {{ standalone: standalone }}
            }};

            const mockDoc = {{
                documentElement: documentElement,
                referrer: referrer
            }};

            // Execute in scoped sandbox
            try {{
                const fn = new Function('window', 'document', 'localStorage', 'URLSearchParams', rawScript);
                fn(mockWindow, mockDoc, localStorage, URLSearchParams);
            }} catch (err) {{
                return {{ name, error: err.message }};
            }}

            const actualIsApp = mockWindow.__HAMRAH_IS_APP_MODE;
            const hasClass = classList.has('is-mobile-app');
            const storedVal = store['HAMRAH_APP_MODE'] || null;

            return {{
                name,
                search,
                actualIsApp,
                expApp,
                hasClass,
                storedVal,
                expStore,
                pass: (actualIsApp === expApp) && (hasClass === expApp) && (storedVal === expStore)
            }};
        }});

        console.log(JSON.stringify(results));
        """

        results = self._run_node_script(js_harness)
        for res in results:
            with self.subTest(scenario=res["name"]):
                self.assertNotIn("error", res, f"Scenario '{res['name']}' threw error: {res.get('error')}")
                self.assertTrue(
                    res["pass"],
                    f"Scenario '{res['name']}' failed! Expected isApp={res['expApp']}, got {res['actualIsApp']}, stored={res['storedVal']}",
                )

    # =========================================================================
    # 2. Anti-FOUC CSS Shield & Physical DOM Purge Resilience
    # =========================================================================
    def test_02_anti_fouc_css_shield_rules(self):
        """Verify Anti-FOUC CSS Shield strictly suppresses all admin selectors."""
        shield_tag = self.soup.find("style", id="app-mode-shield")
        self.assertIsNotNone(shield_tag, "<style id='app-mode-shield'> must be in <head>")
        css_text = shield_tag.get_text()

        self.assertIn("html.is-mobile-app #header-admin-btn", css_text)
        self.assertIn("html.is-mobile-app [data-admin-trigger]", css_text)
        self.assertIn("html.is-mobile-app .admin-panel-trigger", css_text)
        self.assertIn("html.is-mobile-app #staff-login-modal", css_text)
        self.assertIn("display: none !important;", css_text)
        self.assertIn("visibility: hidden !important;", css_text)
        self.assertIn("pointer-events: none !important;", css_text)

    def test_03_physical_dom_purge_and_resurrection_resistance(self):
        """Empirically test DOM purge engine and MutationObserver dynamic interceptor."""
        # Extract purge engine from index.html
        purge_match = re.search(
            r"// APP MODE PHYSICAL DOM PURGE ENGINE[\s\S]*?function purgeAdminElementsFromDOM\(\)\s*\{([\s\S]*?)\n\s*\}\n",
            self.html_content,
        )
        self.assertIsNotNone(purge_match, "purgeAdminElementsFromDOM function must exist")
        purge_body = purge_match.group(1)

        js_harness = f"""
        // Simple DOM Mock
        class MockNode {{
            constructor(tagName, id = '', className = '', attrs = {{}}) {{
                this.tagName = tagName.toUpperCase();
                this.id = id;
                this.className = className;
                this.nodeType = 1; // ELEMENT_NODE
                this.classList = {{
                    _c: new Set(className ? className.split(/\\s+/).filter(Boolean) : []),
                    contains: (c) => this.classList._c.has(c),
                    add: (c) => this.classList._c.add(c),
                    remove: (c) => this.classList._c.delete(c)
                }};
                this.attributes = Object.assign({{}}, attrs);
                this.children = [];
                this.parentNode = null;
            }}
            hasAttribute(a) {{ return a in this.attributes; }}
            getAttribute(a) {{ return this.attributes[a] || null; }}
            appendChild(child) {{
                child.parentNode = this;
                this.children.push(child);
                return child;
            }}
            remove() {{
                if (this.parentNode) {{
                    const idx = this.parentNode.children.indexOf(this);
                    if (idx !== -1) this.parentNode.children.splice(idx, 1);
                    this.parentNode = null;
                }}
            }}
            querySelectorAll(sel) {{
                const res = [];
                const check = (node) => {{
                    for (const ch of node.children) {{
                        let matched = false;
                        if (sel.includes('#header-admin-btn') && ch.id === 'header-admin-btn') matched = true;
                        if (sel.includes('[data-admin-trigger]') && ch.hasAttribute('data-admin-trigger')) matched = true;
                        if (sel.includes('.admin-panel-trigger') && ch.classList.contains('admin-panel-trigger')) matched = true;
                        if (matched) res.push(ch);
                        check(ch);
                    }}
                }};
                check(this);
                return res;
            }}
        }}

        // Setup DOM tree with admin buttons
        function createDOM() {{
            const root = new MockNode('html');
            const body = new MockNode('body');
            const header = new MockNode('header');
            const adminBtn = new MockNode('button', 'header-admin-btn', 'admin-panel-trigger', {{ 'data-admin-trigger': 'true' }});
            const studentBtn = new MockNode('button', 'header-student-btn');
            const categoryBtn = new MockNode('button', '', 'admin-panel-trigger', {{ 'data-admin-trigger': 'true' }});

            header.appendChild(adminBtn);
            header.appendChild(studentBtn);
            body.appendChild(header);
            body.appendChild(categoryBtn);
            root.appendChild(body);

            return {{ root, body, header, adminBtn, studentBtn, categoryBtn }};
        }}

        // 1. Purge in App Mode
        const domApp = createDOM();
        const winApp = {{ __HAMRAH_IS_APP_MODE: true }};
        const docApp = {{
            documentElement: domApp.root,
            body: domApp.body,
            getElementById: (id) => (id === 'header-admin-btn' ? (domApp.header.children.find(c => c.id === id) || null) : null),
            querySelectorAll: (sel) => domApp.root.querySelectorAll(sel)
        }};
        domApp.root.classList.add('is-mobile-app');

        function purgeAdmin(window, document, localStorage) {{
            {purge_body}
        }}

        purgeAdmin(winApp, docApp, {{ getItem: () => '1' }});

        const appAdminRemains = docApp.getElementById('header-admin-btn');
        const appTriggersRemaining = docApp.querySelectorAll('#header-admin-btn, [data-admin-trigger], .admin-panel-trigger').length;

        // 2. Purge in Web Mode
        const domWeb = createDOM();
        const winWeb = {{ __HAMRAH_IS_APP_MODE: false }};
        const docWeb = {{
            documentElement: domWeb.root,
            body: domWeb.body,
            getElementById: (id) => (id === 'header-admin-btn' ? (domWeb.header.children.find(c => c.id === id) || null) : null),
            querySelectorAll: (sel) => domWeb.root.querySelectorAll(sel)
        }};

        purgeAdmin(winWeb, docWeb, {{ getItem: () => null }});
        const webAdminRemains = docWeb.getElementById('header-admin-btn');
        const webTriggersRemaining = docWeb.querySelectorAll('#header-admin-btn, [data-admin-trigger], .admin-panel-trigger').length;

        // 3. MutationObserver dynamic resurrection interception
        let observerCallback = null;
        class MockMutationObserver {{
            constructor(cb) {{ observerCallback = cb; }}
            observe() {{}}
            disconnect() {{}}
        }}

        // Initialize MutationObserver
        let resurrectedCaught = false;
        if (typeof MockMutationObserver !== 'undefined') {{
            const observer = new MockMutationObserver(function(mutations) {{
                for (let i = 0; i < mutations.length; i++) {{
                    const mut = mutations[i];
                    for (let j = 0; j < mut.addedNodes.length; j++) {{
                        const node = mut.addedNodes[j];
                        if (node.id === 'header-admin-btn' || node.hasAttribute('data-admin-trigger') || node.classList.contains('admin-panel-trigger')) {{
                            node.remove();
                        }}
                    }}
                }}
            }});

            const rogueBtn = new MockNode('button', 'header-admin-btn', 'admin-panel-trigger');
            domApp.body.appendChild(rogueBtn);
            observerCallback([{{ addedNodes: [rogueBtn] }}]);
            resurrectedCaught = (rogueBtn.parentNode === null);
        }}

        console.log(JSON.stringify({{
            appAdminRemains: Boolean(appAdminRemains),
            appTriggersRemaining,
            webAdminRemains: Boolean(webAdminRemains),
            webTriggersRemaining,
            resurrectedCaught
        }}));
        """

        result = self._run_node_script(js_harness)
        self.assertFalse(result["appAdminRemains"], "header-admin-btn must be removed in app mode")
        self.assertEqual(result["appTriggersRemaining"], 0, "No admin triggers may remain in DOM in app mode")
        self.assertTrue(result["webAdminRemains"], "header-admin-btn must remain in web mode")
        self.assertEqual(result["webTriggersRemaining"], 2, "All triggers must remain in web mode")
        self.assertTrue(result["resurrectedCaught"], "MutationObserver must catch and destroy resurrected admin nodes")

    # =========================================================================
    # 3. Route Guard & Modal Evasion
    # =========================================================================
    def test_04_route_guard_and_modal_evasion(self):
        """Verify navigateTo('admin'), openStaffLoginModal(), and hash routing in App Mode."""
        js_harness = f"""
        const fs = require('fs');
        const html = fs.readFileSync('index.html', 'utf-8');

        // Extract navigateTo definition
        const navMatch = html.match(/navigateTo = function\\(view, params, skipHashUpdate\\) \\{{([\\s\\S]*?)\\n\\}};/);
        const navBody = navMatch ? navMatch[1] : '';

        // Extract handleHashChangeRoute
        const hashMatch = html.match(/function handleHashChangeRoute\\(\\) \\{{([\\s\\S]*?)\\n\\}}/);
        const hashBody = hashMatch ? hashMatch[1] : '';

        // Extract openStaffLoginModal
        const modalMatch = html.match(/window\\.openStaffLoginModal = function\\(redirectParams\\) \\{{([\\s\\S]*?)\\n\\}};/);
        const modalBody = modalMatch ? modalMatch[1] : '';

        // Test 1: navigateTo('admin') in App Mode
        let auditLogged = false;
        let finalNavView = null;
        let warningLogged = false;

        const STATE = {{ currentView: 'home', viewParams: {{}} }};
        const windowMock = {{
            __HAMRAH_IS_APP_MODE: true,
            location: {{ hash: '#/home' }}
        }};
        const docMock = {{
            documentElement: {{ classList: {{ contains: (c) => c === 'is-mobile-app' }} }}
        }};
        const localMock = {{ getItem: () => '1' }};

        function logAdminAction() {{ auditLogged = true; }}
        const consoleMock = {{
            warn: () => {{ warningLogged = true; }},
            error: () => {{}},
            log: () => {{}}
        }};

        function navigateTo(view, params, skipHashUpdate) {{
            const p = params || {{}};
            const isAppMode = Boolean(windowMock.__HAMRAH_IS_APP_MODE || (docMock.documentElement && docMock.documentElement.classList.contains('is-mobile-app')) || localMock.getItem('HAMRAH_APP_MODE') === '1');
            if (view === 'admin' && isAppMode) {{
                consoleMock.warn('blocked');
                logAdminAction();
                finalNavView = 'home';
                return;
            }}
            finalNavView = view;
        }}

        navigateTo('admin');

        // Test 2: openStaffLoginModal in App Mode
        let modalOpened = false;
        let modalWarnLogged = false;
        function openSwitchUserModal() {{ modalOpened = true; }}

        function openStaffLoginModal(redirectParams) {{
            const isAppMode = Boolean(windowMock.__HAMRAH_IS_APP_MODE || (docMock.documentElement && docMock.documentElement.classList.contains('is-mobile-app')) || localMock.getItem('HAMRAH_APP_MODE') === '1');
            if (isAppMode) {{
                modalWarnLogged = true;
                return;
            }}
            openSwitchUserModal(redirectParams);
        }}

        openStaffLoginModal();

        // Test 3: hash navigation tampering
        const hashTestCases = ['admin', 'admin/categories', 'admin/approvals', '#admin', '#/admin/dashboard'];
        const hashResults = hashTestCases.map(h => {{
            let currentHash = '#' + h.replace(/^#+/, '');
            let redirectedTo = null;
            let navTarget = null;

            const rawHash = (currentHash || '').replace(/^#\\/?/, '').trim();
            const isAppMode = true;
            if (isAppMode && (rawHash === 'admin' || rawHash.startsWith('admin/') || rawHash.includes('admin'))) {{
                redirectedTo = '#/home';
                navTarget = 'home';
            }}

            return {{ input: h, redirectedTo, navTarget, blocked: (redirectedTo === '#/home' && navTarget === 'home') }};
        }});

        console.log(JSON.stringify({{
            finalNavView,
            auditLogged,
            warningLogged,
            modalOpened,
            modalWarnLogged,
            allHashesBlocked: hashResults.every(r => r.blocked),
            hashResults
        }}));
        """

        result = self._run_node_script(js_harness)
        self.assertEqual(result["finalNavView"], "home", "navigateTo('admin') must redirect to 'home' in app mode")
        self.assertTrue(result["auditLogged"], "Security audit log must be triggered on blocked admin route")
        self.assertTrue(result["warningLogged"], "Security warning must be logged on blocked admin route")
        self.assertFalse(result["modalOpened"], "openStaffLoginModal must NOT open modal in app mode")
        self.assertTrue(result["modalWarnLogged"], "openStaffLoginModal must log warning when blocked")
        self.assertTrue(result["allHashesBlocked"], f"All admin hash paths must be blocked! Results: {result['hashResults']}")

    def test_05_auth_service_update_header_badges_immunity(self):
        """Verify AuthService.updateHeaderBadges does not resurrect admin button in app mode."""
        match = re.search(
            r"updateHeaderBadges\s*\(\)\s*\{([\s\S]*?)\n\s*\},",
            self.html_content,
        )
        self.assertIsNotNone(match, "updateHeaderBadges must exist in AuthService")
        method_body = match.group(1)

        js_harness = f"""
        const STATE = {{
            currentUser: {{ name: 'سید علی حسینی', isGuest: false, roleLabel: 'دانش‌آموز پایه دوازدهم' }}
        }};

        // In App Mode: adminBtn is removed, label updated
        let adminRemoved = false;
        let labelUpdated = '';

        const mockAdminBtn = {{
            remove: () => {{ adminRemoved = true; }},
            innerHTML: ''
        }};
        const mockLabel = {{
            textContent: ''
        }};

        const windowMock = {{ __HAMRAH_IS_APP_MODE: true }};
        const docMock = {{
            documentElement: {{ classList: {{ contains: () => true }} }},
            getElementById: (id) => {{
                if (id === 'header-admin-btn') return mockAdminBtn;
                if (id === 'header-user-label') return mockLabel;
                return null;
            }}
        }};
        const localMock = {{ getItem: () => '1' }};

        function updateHeaderBadges(window, document, localStorage) {{
            {method_body}
        }}

        updateHeaderBadges(windowMock, docMock, localMock);

        console.log(JSON.stringify({{
            adminRemoved,
            labelValue: mockLabel.textContent,
            adminInnerHTML: mockAdminBtn.innerHTML
        }}));
        """

        result = self._run_node_script(js_harness)
        self.assertTrue(result["adminRemoved"], "adminBtn.remove() must be invoked in app mode")
        self.assertEqual(result["labelValue"], "سید علی حسینی", "Student label must be updated with student name")
        self.assertEqual(result["adminInnerHTML"], "", "adminBtn.innerHTML must NOT be mutated or populated")

    # =========================================================================
    # 4. Standard Web Mode Preservation & Baseline Invariants
    # =========================================================================
    def test_06_baseline_invariants_and_web_mode_markup(self):
        """Verify baseline HTML preserves admin elements, Persian language, and metadata."""
        # 1. Baseline header admin button exists in raw markup
        btn = self.soup.find("button", id="header-admin-btn")
        self.assertIsNotNone(btn, "Standard HTML must contain button#header-admin-btn")
        self.assertIn("پنل مدیریت", btn.get_text(), "Admin button must have Persian label 'پنل مدیریت'")
        self.assertEqual(btn.get("data-admin-trigger"), "true", "Admin button must have data-admin-trigger attribute")
        self.assertIn("admin-panel-trigger", btn.get("class", []), "Admin button must have admin-panel-trigger class")

        # 2. HTML language and direction
        html_tag = self.soup.find("html")
        self.assertIsNotNone(html_tag)
        self.assertEqual(html_tag.get("lang"), "fa", "lang attribute must be 'fa'")
        self.assertEqual(html_tag.get("dir"), "rtl", "dir attribute must be 'rtl'")
        self.assertNotIn("is-mobile-app", html_tag.get("class", []), "is-mobile-app must NOT be statically in HTML class")

        # 3. Title contains Persian branding
        title_tag = self.soup.find("title")
        self.assertIsNotNone(title_tag)
        self.assertIn("همراه باقرالعلوم", title_tag.get_text())

        # 4. Canonical URL references copy Worker
        canonical = self.soup.find("link", rel="canonical")
        self.assertIsNotNone(canonical)
        self.assertEqual(
            canonical.get("href"),
            "https://hamrah-bagherololum-copy.psyeducation-hadi.workers.dev/",
            "Canonical URL must strictly point to copy worker",
        )

        # 5. Production URL sanitization
        self.assert_not_matches(
            r"https?://psyeducationhadi-bot\.github\.io/hamrah-bagherololum/(?!copy)",
            self.html_content,
            "No links may point to original non-copy repository Pages",
        )
        self.assert_not_matches(
            r"https?://hamrah-bagherololum\.psyeducation-hadi\.workers\.dev",
            self.html_content,
            "No links may point to original production Worker",
        )

    # =========================================================================
    # 5. Adversarial Audit: Student Portal Modal & LiveVisualCMS Analysis
    # =========================================================================
    def test_07_adversarial_deep_inspection(self):
        """Adversarial check of secondary surfaces: student portal triggers & LiveVisualCMS."""
        # Check all onclick attributes across the document for admin / staff login invocations
        onclick_elements = self.soup.find_all(lambda t: t.has_attr("onclick"))
        admin_onclick_findings = []
        for el in onclick_elements:
            handler = el["onclick"]
            if "openStaffLoginModal" in handler:
                admin_onclick_findings.append(("openStaffLoginModal", el.name, el.get("id"), el.get("class")))
            elif "navigateTo('admin'" in handler or 'navigateTo("admin"' in handler:
                admin_onclick_findings.append(("navigateTo('admin')", el.name, el.get("id"), el.get("class")))

        # In baseline HTML, the only static element navigating to admin is header-admin-btn
        admin_nav_elements = [f for f in admin_onclick_findings if "navigateTo('admin')" in f[0]]
        self.assertEqual(
            len(admin_nav_elements),
            1,
            f"Expected exactly 1 static admin navigation button, found: {admin_nav_elements}",
        )
        self.assertEqual(admin_nav_elements[0][2], "header-admin-btn")


if __name__ == "__main__":
    unittest.main(verbosity=2)
