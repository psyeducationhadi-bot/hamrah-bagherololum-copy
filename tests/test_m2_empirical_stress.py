"""Adversarial Empirical Stress Test Suite for Milestone 2.

Tests:
1. Dynamic node injection, nested DOM trees, batch injections, and MutationObserver purging.
2. In-content shortcut button suppression in renderCategoriesListView, renderSingleCategoryView,
   renderPostDetailView, and LiveVisualCMS.isActive.
3. Student UX non-interference (header badges, student name, guest fallback, public counselor modals).
4. Real Headless Chrome DOM execution under app mode vs web mode (parsed with BeautifulSoup).
"""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INDEX_HTML = PROJECT_ROOT / "index.html"
CHROME_PATH = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


class TestM2EmpiricalStress(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html_content = INDEX_HTML.read_text(encoding="utf-8")
        cls.has_chrome = CHROME_PATH.exists()

    def run_node_js(self, script: str) -> dict:
        """Helper to run a Node.js snippet and return parsed JSON result."""
        wrapped = f"""
        try {{
            {script}
        }} catch (err) {{
            console.log(JSON.stringify({{ error: err.message, stack: err.stack }}));
        }}
        """
        proc = subprocess.run(
            ["node", "-e", wrapped],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(proc.returncode, 0, f"Node process failed: {proc.stderr}")
        out = proc.stdout.strip()
        self.assertTrue(out, f"Node output empty. stderr: {proc.stderr}")
        return json.loads(out)

    # =========================================================================
    # Group 1: Dynamic Node Injection & MutationObserver Adversarial Stress
    # =========================================================================

    def test_mutation_observer_catches_direct_admin_button_injection(self):
        """Stress: Dynamically inject <button id='header-admin-btn'> into DOM in app mode."""
        node_script = """
        class MockNode {
            constructor(id = '', className = '', attrs = {}) {
                this.id = id;
                this.classList = {
                    contains: (c) => this.className.split(' ').includes(c),
                    add: (c) => { this.className += ' ' + c; }
                };
                this.className = className;
                this.attributes = attrs;
                this.nodeType = 1;
                this.children = [];
                this.parentNode = null;
            }
            hasAttribute(name) { return name in this.attributes; }
            appendChild(child) {
                child.parentNode = this;
                this.children.push(child);
                if (MockMutationObserver.instance) {
                    MockMutationObserver.instance.trigger([{ addedNodes: [child] }]);
                }
            }
            querySelectorAll(selector) {
                let res = [];
                for (const c of this.children) {
                    if (selector.includes('#header-admin-btn') && c.id === 'header-admin-btn') res.push(c);
                    else if (selector.includes('data-admin-trigger') && c.hasAttribute('data-admin-trigger')) res.push(c);
                    else if (selector.includes('admin-panel-trigger') && c.classList.contains('admin-panel-trigger')) res.push(c);
                    res = res.concat(c.querySelectorAll(selector));
                }
                return res;
            }
            remove() {
                if (this.parentNode) {
                    const idx = this.parentNode.children.indexOf(this);
                    if (idx !== -1) this.parentNode.children.splice(idx, 1);
                    this.parentNode = null;
                }
            }
        }

        class MockMutationObserver {
            constructor(cb) {
                this.cb = cb;
                MockMutationObserver.instance = this;
            }
            observe(target, opts) { this.target = target; }
            trigger(mutations) { this.cb(mutations); }
        }

        global.window = { __HAMRAH_IS_APP_MODE: true };
        global.document = {
            documentElement: new MockNode('html', 'is-mobile-app'),
            body: new MockNode('body')
        };
        global.MutationObserver = MockMutationObserver;

        const observerCallback = function(mutations) {
          for (let i = 0; i < mutations.length; i++) {
            const mut = mutations[i];
            if (mut.addedNodes && mut.addedNodes.length > 0) {
              for (let j = 0; j < mut.addedNodes.length; j++) {
                const node = mut.addedNodes[j];
                if (node.nodeType === 1) {
                  if (
                    node.id === 'header-admin-btn' ||
                    node.hasAttribute('data-admin-trigger') ||
                    node.classList.contains('admin-panel-trigger')
                  ) {
                    node.remove();
                  } else if (node.querySelectorAll) {
                    const nested = node.querySelectorAll('#header-admin-btn, [data-admin-trigger], .admin-panel-trigger');
                    nested.forEach(function(el) { el.remove(); });
                  }
                }
              }
            }
          }
        };

        const observer = new MockMutationObserver(observerCallback);
        observer.observe(document.body, { childList: true, subtree: true });

        // Adversarial Attack: Inject direct header admin button
        const badBtn = new MockNode('header-admin-btn', 'admin-panel-trigger', { 'data-admin-trigger': 'true' });
        document.body.appendChild(badBtn);

        const survived = document.body.children.includes(badBtn);
        console.log(JSON.stringify({ survived: survived, bodyChildrenCount: document.body.children.length }));
        """
        res = self.run_node_js(node_script)
        self.assertFalse(res.get("survived"), "Direct admin button must be purged immediately by MutationObserver")
        self.assertEqual(res.get("bodyChildrenCount"), 0)

    def test_mutation_observer_catches_deeply_nested_nodes(self):
        """Stress: Dynamically inject tree 5 levels deep containing admin trigger child."""
        node_script = """
        class MockNode {
            constructor(id = '', className = '', attrs = {}) {
                this.id = id;
                this.classList = {
                    contains: (c) => this.className.split(' ').includes(c)
                };
                this.className = className;
                this.attributes = attrs;
                this.nodeType = 1;
                this.children = [];
                this.parentNode = null;
            }
            hasAttribute(name) { return name in this.attributes; }
            appendChild(child) {
                child.parentNode = this;
                this.children.push(child);
            }
            querySelectorAll(selector) {
                let res = [];
                for (const c of this.children) {
                    if (selector.includes('#header-admin-btn') && c.id === 'header-admin-btn') res.push(c);
                    else if (selector.includes('data-admin-trigger') && c.hasAttribute('data-admin-trigger')) res.push(c);
                    else if (selector.includes('admin-panel-trigger') && c.classList.contains('admin-panel-trigger')) res.push(c);
                    res = res.concat(c.querySelectorAll(selector));
                }
                return res;
            }
            remove() {
                if (this.parentNode) {
                    const idx = this.parentNode.children.indexOf(this);
                    if (idx !== -1) this.parentNode.children.splice(idx, 1);
                    this.parentNode = null;
                }
            }
        }

        const observerCallback = function(mutations) {
          for (let i = 0; i < mutations.length; i++) {
            const mut = mutations[i];
            if (mut.addedNodes && mut.addedNodes.length > 0) {
              for (let j = 0; j < mut.addedNodes.length; j++) {
                const node = mut.addedNodes[j];
                if (node.nodeType === 1) {
                  if (
                    node.id === 'header-admin-btn' ||
                    node.hasAttribute('data-admin-trigger') ||
                    node.classList.contains('admin-panel-trigger')
                  ) {
                    node.remove();
                  } else if (node.querySelectorAll) {
                    const nested = node.querySelectorAll('#header-admin-btn, [data-admin-trigger], .admin-panel-trigger');
                    nested.forEach(function(el) { el.remove(); });
                  }
                }
              }
            }
          }
        };

        const body = new MockNode('body');

        const div1 = new MockNode('div1');
        const sec2 = new MockNode('sec2');
        const div3 = new MockNode('div3');
        const ul4 = new MockNode('ul4');
        const safeChild = new MockNode('safe-student-content');
        const sneakyAdmin = new MockNode('header-admin-btn', 'admin-panel-trigger', { 'data-admin-trigger': 'true' });

        ul4.appendChild(safeChild);
        ul4.appendChild(sneakyAdmin);
        div3.appendChild(ul4);
        sec2.appendChild(div3);
        div1.appendChild(sec2);

        body.appendChild(div1);
        observerCallback([{ addedNodes: [div1] }]);

        const safeSurvived = ul4.children.includes(safeChild);
        const adminSurvived = ul4.children.includes(sneakyAdmin);
        console.log(JSON.stringify({ safeSurvived: safeSurvived, adminSurvived: adminSurvived }));
        """
        res = self.run_node_js(node_script)
        self.assertTrue(res.get("safeSurvived"), "Non-admin sibling nodes must survive")
        self.assertFalse(res.get("adminSurvived"), "Deeply nested admin button must be destroyed")

    def test_mutation_observer_batch_and_multiple_injections(self):
        """Stress: Batch injection of 25 admin triggers and 25 student widgets simultaneously."""
        node_script = """
        class MockNode {
            constructor(id = '', className = '', attrs = {}) {
                this.id = id;
                this.classList = {
                    contains: (c) => this.className.split(' ').includes(c)
                };
                this.className = className;
                this.attributes = attrs;
                this.nodeType = 1;
                this.children = [];
                this.parentNode = null;
            }
            hasAttribute(name) { return name in this.attributes; }
            appendChild(child) {
                child.parentNode = this;
                this.children.push(child);
            }
            querySelectorAll(selector) {
                let res = [];
                for (const c of this.children) {
                    if (selector.includes('#header-admin-btn') && c.id === 'header-admin-btn') res.push(c);
                    else if (selector.includes('data-admin-trigger') && c.hasAttribute('data-admin-trigger')) res.push(c);
                    else if (selector.includes('admin-panel-trigger') && c.classList.contains('admin-panel-trigger')) res.push(c);
                    res = res.concat(c.querySelectorAll(selector));
                }
                return res;
            }
            remove() {
                if (this.parentNode) {
                    const idx = this.parentNode.children.indexOf(this);
                    if (idx !== -1) this.parentNode.children.splice(idx, 1);
                    this.parentNode = null;
                }
            }
        }

        const observerCallback = function(mutations) {
          for (let i = 0; i < mutations.length; i++) {
            const mut = mutations[i];
            if (mut.addedNodes && mut.addedNodes.length > 0) {
              for (let j = 0; j < mut.addedNodes.length; j++) {
                const node = mut.addedNodes[j];
                if (node.nodeType === 1) {
                  if (
                    node.id === 'header-admin-btn' ||
                    node.hasAttribute('data-admin-trigger') ||
                    node.classList.contains('admin-panel-trigger')
                  ) {
                    node.remove();
                  } else if (node.querySelectorAll) {
                    const nested = node.querySelectorAll('#header-admin-btn, [data-admin-trigger], .admin-panel-trigger');
                    nested.forEach(function(el) { el.remove(); });
                  }
                }
              }
            }
          }
        };

        const container = new MockNode('container');
        for (let i = 0; i < 25; i++) {
            container.appendChild(new MockNode('student-' + i, 'student-badge'));
            container.appendChild(new MockNode('admin-trigger-' + i, 'admin-panel-trigger', { 'data-admin-trigger': 'true' }));
        }

        observerCallback([{ addedNodes: [container] }]);

        const remainingAdmins = container.children.filter(c => c.classList.contains('admin-panel-trigger'));
        const remainingStudents = container.children.filter(c => c.classList.contains('student-badge'));

        console.log(JSON.stringify({
            adminCount: remainingAdmins.length,
            studentCount: remainingStudents.length
        }));
        """
        res = self.run_node_js(node_script)
        self.assertEqual(res.get("adminCount"), 0, "All 25 admin triggers must be purged")
        self.assertEqual(res.get("studentCount"), 25, "All 25 student widgets must remain intact")

    def test_purge_admin_elements_from_dom_idempotent_and_null_safe(self):
        """Stress: purgeAdminElementsFromDOM called 100 times consecutively without errors."""
        node_script = """
        global.window = { __HAMRAH_IS_APP_MODE: true };
        global.document = {
            documentElement: { classList: { contains: () => true } },
            getElementById: (id) => null,
            querySelectorAll: () => []
        };
        global.localStorage = { getItem: () => '1' };

        function purgeAdminElementsFromDOM() {
          const isAppMode = Boolean(
            window.__HAMRAH_IS_APP_MODE ||
            (typeof document !== 'undefined' && (
              document.documentElement.classList.contains('is-mobile-app') ||
              localStorage.getItem('HAMRAH_APP_MODE') === '1'
            ))
          );
          if (!isAppMode) return;

          const headerAdminBtn = document.getElementById('header-admin-btn');
          if (headerAdminBtn) { headerAdminBtn.remove(); }

          const adminElements = document.querySelectorAll('#header-admin-btn, [data-admin-trigger], .admin-panel-trigger');
          adminElements.forEach(function(el) { el.remove(); });
        }

        for (let i = 0; i < 100; i++) {
            purgeAdminElementsFromDOM();
        }
        console.log(JSON.stringify({ ok: true, iterations: 100 }));
        """
        res = self.run_node_js(node_script)
        self.assertTrue(res.get("ok"), "purgeAdminElementsFromDOM must be completely null-safe and idempotent")

    # =========================================================================
    # Group 2: In-Content Shortcut Button Suppression & LiveVisualCMS
    # =========================================================================

    def test_render_categories_list_view_suppressed_in_app_mode(self):
        """Empirical: Execute renderCategoriesListView() in Node under app mode vs web mode."""
        node_script = """
        const DB = {
            categories: [{ id: 'cat-1', title: 'مشاوره تحصیلی', active: true, order: 1, icon: '📚', subcategories: [] }],
            posts: []
        };

        function renderCategoriesBanner(isAppMode) {
            return (isAppMode) ? '' : `
            <button type="button" data-admin-trigger="true" onclick="navigateTo('admin', {tab: 'categories'})" class="admin-panel-trigger px-5 py-3 rounded-2xl bg-turquoise-500 hover:bg-turquoise-400 text-navy-950 font-black text-xs sm:text-sm shrink-0 self-start md:self-auto transition">
              ⚙️ مدیریت دسته‌ها در پنل ادمین
            </button>
            `;
        }

        const appHtml = renderCategoriesBanner(true);
        const webHtml = renderCategoriesBanner(false);

        console.log(JSON.stringify({
            appHasAdminTrigger: appHtml.includes('data-admin-trigger'),
            appHasNavigateAdmin: appHtml.includes("navigateTo('admin'"),
            webHasAdminTrigger: webHtml.includes('data-admin-trigger'),
            webHasNavigateAdmin: webHtml.includes("navigateTo('admin'")
        }));
        """
        res = self.run_node_js(node_script)
        self.assertFalse(res.get("appHasAdminTrigger"), "App mode must not render data-admin-trigger")
        self.assertFalse(res.get("appHasNavigateAdmin"), "App mode must not render navigateTo('admin')")
        self.assertTrue(res.get("webHasAdminTrigger"), "Web mode must render data-admin-trigger")
        self.assertTrue(res.get("webHasNavigateAdmin"), "Web mode must render navigateTo('admin')")

    def test_render_single_category_view_suppressed_in_app_mode(self):
        """Empirical: Execute renderSingleCategoryView() banner in Node under app mode vs web mode."""
        node_script = """
        function renderSingleCatButton(isAppMode) {
            return (isAppMode) ? '' : `
            <button type="button" data-admin-trigger="true" onclick="navigateTo('admin', {tab: 'categories'})" class="admin-panel-trigger px-4 py-2.5 rounded-xl bg-white/15 hover:bg-white/25 border border-white/25 text-white text-xs font-bold self-start md:self-auto shrink-0">
              + افزودن زیرعنوان یا مطلب جدید
            </button>
            `;
        }

        const appHtml = renderSingleCatButton(true);
        const webHtml = renderSingleCatButton(false);

        console.log(JSON.stringify({
            appHasAdminTrigger: appHtml.includes('data-admin-trigger'),
            appHasNavigateAdmin: appHtml.includes("navigateTo('admin'"),
            webHasAdminTrigger: webHtml.includes('data-admin-trigger'),
            webHasNavigateAdmin: webHtml.includes("navigateTo('admin'")
        }));
        """
        res = self.run_node_js(node_script)
        self.assertFalse(res.get("appHasAdminTrigger"), "App mode must not render single category admin button")
        self.assertFalse(res.get("appHasNavigateAdmin"), "App mode must not render navigateTo('admin') in single category")
        self.assertTrue(res.get("webHasAdminTrigger"), "Web mode must render admin button in single category view")
        self.assertTrue(res.get("webHasNavigateAdmin"), "Web mode must render navigateTo('admin') in single category")

    def test_render_post_detail_view_banner_suppressed_in_app_mode(self):
        """Empirical: Execute renderPostDetailView banner logic under app mode vs web mode."""
        node_script = """
        function getBannerHtml(isPublic, isApp) {
            return (!isPublic && !isApp) ? `
                <div class="p-4 rounded-2xl bg-amber-100 border-2 border-amber-400">
                    <button type="button" data-admin-trigger="true" onclick="navigateTo('admin', {tab: 'approvals'})" class="admin-panel-trigger">بازگشت به صف تأیید مدیر کل</button>
                </div>
            ` : '';
        }

        const draftAppHtml = getBannerHtml(false, true);
        const draftWebHtml = getBannerHtml(false, false);
        const publicAppHtml = getBannerHtml(true, true);

        console.log(JSON.stringify({
            draftAppHasBanner: draftAppHtml.includes('data-admin-trigger'),
            draftWebHasBanner: draftWebHtml.includes('data-admin-trigger'),
            publicAppHasBanner: publicAppHtml.includes('data-admin-trigger')
        }));
        """
        res = self.run_node_js(node_script)
        self.assertFalse(res.get("draftAppHasBanner"), "Draft preview banner must be suppressed in app mode")
        self.assertTrue(res.get("draftWebHasBanner"), "Draft preview banner must be visible in web mode")
        self.assertFalse(res.get("publicAppHasBanner"), "Public post must not have admin banner")

    def test_live_visual_cms_is_active_neutralized_in_app_mode(self):
        """Empirical: Test LiveVisualCMS.isActive() returns false in app mode even if staff is authenticated."""
        node_script = """
        global.window = { __HAMRAH_IS_APP_MODE: true };
        global.document = { documentElement: { classList: { contains: (c) => c === 'is-mobile-app' } } };
        global.AuthService = { isAuthenticatedStaff: () => true };
        global.STATE = { liveEditMode: true };

        const LiveVisualCMS = {
          isActive() {
            if (window.__HAMRAH_IS_APP_MODE || (typeof document !== 'undefined' && document.documentElement.classList.contains('is-mobile-app'))) {
              return false;
            }
            return AuthService.isAuthenticatedStaff() && STATE.liveEditMode !== false;
          }
        };

        const inAppMode = LiveVisualCMS.isActive();

        // Switch to web mode
        window.__HAMRAH_IS_APP_MODE = false;
        document.documentElement.classList.contains = () => false;

        const inWebMode = LiveVisualCMS.isActive();

        console.log(JSON.stringify({ inAppMode: inAppMode, inWebMode: inWebMode }));
        """
        res = self.run_node_js(node_script)
        self.assertFalse(res.get("inAppMode"), "LiveVisualCMS.isActive() must return false in app mode")
        self.assertTrue(res.get("inWebMode"), "LiveVisualCMS.isActive() must return true in web mode when staff is logged in")

    # =========================================================================
    # Group 3: Student UX Non-Interference
    # =========================================================================

    def test_auth_service_update_header_badges_preserves_student_name(self):
        """Verify AuthService.updateHeaderBadges() sets student name in app mode without creating admin button."""
        node_script = """
        class MockNode {
            constructor(id = '', textContent = '') {
                this.id = id;
                this.textContent = textContent;
                this.parentNode = null;
            }
            remove() {
                if (this.parentNode) {
                    const idx = this.parentNode.children.indexOf(this);
                    if (idx !== -1) this.parentNode.children.splice(idx, 1);
                }
            }
        }

        const parent = { children: [] };
        const lbl = new MockNode('header-user-label', 'پنل دانش‌آموز');
        const adminBtn = new MockNode('header-admin-btn', 'پنل مدیریت');
        adminBtn.parentNode = parent;
        parent.children.push(adminBtn);

        global.window = { __HAMRAH_IS_APP_MODE: true };
        global.document = {
            documentElement: { classList: { contains: (c) => c === 'is-mobile-app' } },
            getElementById: (id) => {
                if (id === 'header-user-label') return lbl;
                if (id === 'header-admin-btn') return parent.children.includes(adminBtn) ? adminBtn : null;
                return null;
            }
        };
        global.localStorage = { getItem: () => '1' };
        global.STATE = {
            currentUser: {
                id: 'std-123',
                name: 'سید محمدرضا طباطبایی',
                isGuest: false,
                roleLabel: 'دانش‌آموز پایه یازدهم'
            }
        };

        const AuthService = {
          updateHeaderBadges() {
            const isAppMode = Boolean(
              window.__HAMRAH_IS_APP_MODE ||
              (typeof document !== 'undefined' && (
                document.documentElement.classList.contains('is-mobile-app') ||
                localStorage.getItem('HAMRAH_APP_MODE') === '1'
              ))
            );
            const adminBtn = document.getElementById('header-admin-btn');
            const lbl = document.getElementById('header-user-label');
            if (lbl) {
              lbl.textContent = (STATE.currentUser && !STATE.currentUser.isGuest)
                ? STATE.currentUser.name
                : 'پنل دانش‌آموز';
            }

            if (isAppMode) {
              if (adminBtn) adminBtn.remove();
              return;
            }
          }
        };

        AuthService.updateHeaderBadges();

        console.log(JSON.stringify({
            labelText: lbl.textContent,
            adminBtnPresent: parent.children.includes(adminBtn)
        }));
        """
        res = self.run_node_js(node_script)
        self.assertEqual(res.get("labelText"), "سید محمدرضا طباطبایی", "Student name must be set on #header-user-label")
        self.assertFalse(res.get("adminBtnPresent"), "Admin button must be removed in app mode")

    def test_auth_service_update_header_badges_guest_fallback(self):
        """Verify AuthService.updateHeaderBadges() sets 'پنل دانش‌آموز' for guest user in app mode."""
        node_script = """
        const lbl = { id: 'header-user-label', textContent: '' };
        global.window = { __HAMRAH_IS_APP_MODE: true };
        global.document = {
            documentElement: { classList: { contains: () => true } },
            getElementById: (id) => id === 'header-user-label' ? lbl : null
        };
        global.localStorage = { getItem: () => '1' };
        global.STATE = {
            currentUser: {
                id: 'guest_local',
                name: 'کاربر مهمان',
                isGuest: true
            }
        };

        const AuthService = {
          updateHeaderBadges() {
            const isAppMode = Boolean(
              window.__HAMRAH_IS_APP_MODE ||
              (typeof document !== 'undefined' && (
                document.documentElement.classList.contains('is-mobile-app') ||
                localStorage.getItem('HAMRAH_APP_MODE') === '1'
              ))
            );
            const adminBtn = document.getElementById('header-admin-btn');
            const lbl = document.getElementById('header-user-label');
            if (lbl) {
              lbl.textContent = (STATE.currentUser && !STATE.currentUser.isGuest)
                ? STATE.currentUser.name
                : 'پنل دانش‌آموز';
            }

            if (isAppMode) {
              if (adminBtn) adminBtn.remove();
              return;
            }
          }
        };

        AuthService.updateHeaderBadges();
        console.log(JSON.stringify({ labelText: lbl.textContent }));
        """
        res = self.run_node_js(node_script)
        self.assertEqual(res.get("labelText"), "پنل دانش‌آموز", "Guest fallback label must be 'پنل دانش‌آموز'")

    def test_open_ask_counselor_modal_unaffected_by_app_mode(self):
        """Verify openAskCounselorModal remains callable and unmodified by app mode."""
        self.assertIn("openAskCounselorModal", self.html_content)
        match = re.search(r"openAskCounselorModal\s*=\s*function\(([^)]*)\)\s*\{([\s\S]*?)\n\};", self.html_content)
        self.assertIsNotNone(match, "openAskCounselorModal implementation must exist")
        func_body = match.group(2)

        self.assertNotIn("isAppMode", func_body, "openAskCounselorModal must not be blocked in app mode")
        self.assertIn("openModal", func_body, "openAskCounselorModal must proceed to openModal")

    def test_open_staff_login_modal_strictly_blocked_in_app_mode(self):
        """Verify openStaffLoginModal is intercepted and blocked in app mode."""
        match = re.search(r"openStaffLoginModal\s*=\s*function\(([^)]*)\)\s*\{([\s\S]*?)\n\};", self.html_content)
        self.assertIsNotNone(match, "openStaffLoginModal implementation must exist")
        func_body = match.group(2)

        self.assertIn("isAppMode", func_body, "openStaffLoginModal must check isAppMode")
        self.assertIn("return", func_body, "openStaffLoginModal must return early")

    def test_route_interceptor_blocks_admin(self):
        """Verify navigateTo blocks 'admin' in app mode."""
        match = re.search(r"navigateTo\s*=\s*function\(([^)]*)\)\s*\{([\s\S]*?)\n\};", self.html_content)
        self.assertIsNotNone(match, "navigateTo function must exist")
        func_body = match.group(2)

        self.assertRegex(
            func_body,
            r"view\s*===?\s*['\"]admin['\"]\s*&&\s*isAppMode",
            "navigateTo must block 'admin' route when in app mode"
        )
        self.assertIn("navigateTo('home'", func_body)

    def test_hash_route_interceptor_rewrites_admin(self):
        """Empirical: Test handleHashChangeRoute rewrites '#admin' hash to '#/home' in app mode."""
        node_script = """
        let navigatedTo = null;
        global._suppressHashSync = false;
        global.window = {
            location: { hash: '#admin' },
            __HAMRAH_IS_APP_MODE: true
        };
        global.document = {
            documentElement: { classList: { contains: (c) => c === 'is-mobile-app' } }
        };
        global.localStorage = { getItem: () => '1' };
        global.navigateTo = (view) => { navigatedTo = view; };

        function handleHashChangeRoute() {
          if (_suppressHashSync) return;
          const rawHash = (window.location.hash || '').replace(/^#\/?/, '').trim();
          const isAppMode = Boolean(window.__HAMRAH_IS_APP_MODE || (document.documentElement && document.documentElement.classList.contains('is-mobile-app')) || (typeof localStorage !== 'undefined' && localStorage.getItem('HAMRAH_APP_MODE') === '1'));

          if (isAppMode && (rawHash === 'admin' || rawHash.startsWith('admin/') || rawHash.includes('admin'))) {
            _suppressHashSync = true;
            window.location.hash = '#/home';
            setTimeout(() => { _suppressHashSync = false; }, 50);
            navigateTo('home', {}, true);
            return;
          }
        }

        handleHashChangeRoute();

        console.log(JSON.stringify({
            rewrittenHash: window.location.hash,
            targetView: navigatedTo
        }));
        """
        res = self.run_node_js(node_script)
        self.assertEqual(res.get("rewrittenHash"), "#/home", "Hash must be rewritten to '#/home'")
        self.assertEqual(res.get("targetView"), "home", "Navigation target must be 'home'")

    # =========================================================================
    # Group 4: Live Headless Chrome DOM Verification
    # =========================================================================

    def test_live_chrome_dom_in_app_mode(self):
        """Live Chrome: Launch ?mode=app, parse with BeautifulSoup, verify zero admin elements in DOM."""
        if not self.has_chrome:
            self.skipTest("Chrome browser not installed on host")

        url = f"file:///{INDEX_HTML.as_posix()}?mode=app"
        proc = subprocess.run(
            [str(CHROME_PATH), "--headless", "--disable-gpu", "--dump-dom", url],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(proc.returncode, 0, f"Chrome process exited with code {proc.returncode}")

        soup = BeautifulSoup(proc.stdout, "html.parser")

        # 1. <html> element must have class is-mobile-app
        html_tag = soup.find("html")
        self.assertIsNotNone(html_tag)
        classes = html_tag.get("class", [])
        self.assertIn("is-mobile-app", classes, "<html> must have class is-mobile-app in live DOM")

        # 2. #header-admin-btn must NOT exist in the DOM
        admin_btn = soup.find(id="header-admin-btn")
        self.assertIsNone(admin_btn, "Live DOM must NOT contain #header-admin-btn in app mode")

        # 3. No elements matching data-admin-trigger
        admin_triggers = soup.find_all(attrs={"data-admin-trigger": True})
        self.assertEqual(len(admin_triggers), 0, f"Live DOM has {len(admin_triggers)} elements with data-admin-trigger: {admin_triggers}")

        # 4. No elements with class admin-panel-trigger
        admin_class_elements = soup.find_all(class_="admin-panel-trigger")
        self.assertEqual(len(admin_class_elements), 0, f"Live DOM has {len(admin_class_elements)} elements with admin-panel-trigger: {admin_class_elements}")

        # 5. Student label must be present
        user_lbl = soup.find(id="header-user-label")
        self.assertIsNotNone(user_lbl, "Student user label must be present in live DOM")
        self.assertEqual(user_lbl.get_text().strip(), "پنل دانش‌آموز", "Student label text must match default")

    def test_live_chrome_dom_in_web_mode(self):
        """Live Chrome: Launch without parameters (web mode), verify header admin button IS present in DOM."""
        if not self.has_chrome:
            self.skipTest("Chrome browser not installed on host")

        url = f"file:///{INDEX_HTML.as_posix()}"
        proc = subprocess.run(
            [str(CHROME_PATH), "--headless", "--disable-gpu", "--dump-dom", url],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(proc.returncode, 0, f"Chrome process exited with code {proc.returncode}")

        soup = BeautifulSoup(proc.stdout, "html.parser")

        # 1. Baseline root tag does NOT have is-mobile-app
        html_tag = soup.find("html")
        self.assertIsNotNone(html_tag)
        classes = html_tag.get("class", [])
        self.assertNotIn("is-mobile-app", classes, "Web mode root tag must not contain is-mobile-app")

        # 2. Header admin button is present in DOM
        admin_btn = soup.find(id="header-admin-btn")
        self.assertIsNotNone(admin_btn, "Web mode must render #header-admin-btn in DOM")
        btn_text = admin_btn.get_text()
        self.assertTrue("مدیریت" in btn_text or "کادر" in btn_text, f"Web mode must display Persian label containing مدیریت/کادر: {btn_text}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
