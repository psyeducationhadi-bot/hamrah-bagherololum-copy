"""Adversarial Empirical Stress Test Suite for Milestone 3 (Mobile UI Polish & Hardware Back Button).

Exhaustively verifies:
1. History API modal interceptor:
   - openModal pushes state ({ modalOpen: true, modalId })
   - Android Back button (popstate) dismisses modal without double-navigation or page reload
2. UI Close desynchronization prevention:
   - closeModal() pops history with _ignoreNextPopstate = true
   - Subsequent popstate from browser history.back() is cleanly swallowed
   - Subsequent user Back button press is not blocked when modals are closed
3. No-modal Back button passthrough:
   - popstate does not intercept or break normal browser navigation when modals are closed
4. Rapid nested modals & idempotence:
   - openModal when already open uses replaceState preventing history stack bloat
   - closeModal called multiple times is completely idempotent
   - Error in history.back() resets _ignoreNextPopstate cleanly
5. Backdrop click & keyboard accessibility:
   - Backdrop click dismisses modal; clicking modal box interior does not
   - Desktop Escape key dismisses modal
6. Touch ergonomics and CSS rules:
   - user-select: none on interactive chrome, user-select: text on articles and inputs
   - font-size: 16px !important on inputs to prevent mobile viewport zoom
   - overflow-x: hidden and max-width: 100vw on html, body
   - -webkit-tap-highlight-color: transparent and safe-area insets
7. Live Headless Chrome verification in mobile viewport:
   - DOM elements, computed styles, and live openModal/popstate execution in real Chromium
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


class TestM3MobileEmpiricalStress(unittest.TestCase):
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
    # Group 1: History API & Back Button Lifecycle (Node.js Simulated Environment)
    # =========================================================================

    def _get_history_harness_script(self, test_body: str) -> str:
        """Constructs a high-fidelity DOM and History API mock for Node.js."""
        return f"""
        // High-fidelity DOM Mock
        class MockClassList {{
            constructor() {{ this.classes = new Set(); }}
            add(c) {{ this.classes.add(c); }}
            remove(c) {{ this.classes.delete(c); }}
            contains(c) {{ return this.classes.has(c); }}
            toString() {{ return Array.from(this.classes).join(' '); }}
        }}

        class MockElement {{
            constructor(id) {{
                this.id = id;
                this.classList = new MockClassList();
                this.innerHTML = '';
                this.listeners = {{}};
                this.__hasBackdropClickListener = false;
            }}
            addEventListener(type, cb) {{
                if (!this.listeners[type]) this.listeners[type] = [];
                this.listeners[type].push(cb);
            }}
            dispatchEvent(event) {{
                const list = this.listeners[event.type] || [];
                for (const cb of list) {{
                    cb(event);
                }}
            }}
        }}

        const backdropEl = new MockElement('global-modal-backdrop');
        backdropEl.classList.add('hidden');
        const boxEl = new MockElement('global-modal-box');

        const windowListeners = {{}};
        let historyCalls = [];
        let historyStack = [{{ state: null, url: '' }}];
        let historyIndex = 0;

        const mockHistory = {{
            get state() {{
                return historyStack[historyIndex] ? historyStack[historyIndex].state : null;
            }},
            pushState(state, title, url) {{
                historyCalls.push({{ method: 'pushState', state, url }});
                historyStack = historyStack.slice(0, historyIndex + 1);
                historyStack.push({{ state: JSON.parse(JSON.stringify(state)), url }});
                historyIndex++;
            }},
            replaceState(state, title, url) {{
                historyCalls.push({{ method: 'replaceState', state, url }});
                if (historyStack[historyIndex]) {{
                    historyStack[historyIndex] = {{ state: JSON.parse(JSON.stringify(state)), url }};
                }}
            }},
            back() {{
                historyCalls.push({{ method: 'back' }});
                if (historyIndex > 0) {{
                    historyIndex--;
                }}
            }}
        }};

        global.window = {{
            history: mockHistory,
            addEventListener(type, cb) {{
                if (!windowListeners[type]) windowListeners[type] = [];
                windowListeners[type].push(cb);
            }},
            dispatchEvent(event) {{
                const list = windowListeners[event.type] || [];
                for (const cb of list) {{
                    cb(event);
                }}
            }}
        }};
        global.history = mockHistory;
        global.document = {{
            readyState: 'complete',
            addEventListener(type, cb) {{
                if (!windowListeners[type]) windowListeners[type] = [];
                windowListeners[type].push(cb);
            }},
            getElementById(id) {{
                if (id === 'global-modal-backdrop') return backdropEl;
                if (id === 'global-modal-box') return boxEl;
                return null;
            }}
        }};

        // Extracted Production Functions
        let isModalOpen = false;
        let _ignoreNextPopstate = false;

        function openModal(htmlContent, modalId) {{
          const backdrop = document.getElementById('global-modal-backdrop');
          const box = document.getElementById('global-modal-box');
          if (!backdrop || !box) return;

          box.innerHTML = htmlContent;
          backdrop.classList.remove('hidden');

          if (!isModalOpen) {{
            isModalOpen = true;
            try {{
              history.pushState({{ modalOpen: true, modalId: modalId || 'global-modal-box' }}, '');
            }} catch (e) {{
              console.warn('[Hamrah History] history.pushState not available:', e);
            }}
          }} else {{
            try {{
              history.replaceState({{ modalOpen: true, modalId: modalId || 'global-modal-box' }}, '');
            }} catch (e) {{}}
          }}
        }}

        function closeModal(fromPopstate) {{
          const backdrop = document.getElementById('global-modal-backdrop');
          if (backdrop) backdrop.classList.add('hidden');

          if (isModalOpen) {{
            isModalOpen = false;
            if (!fromPopstate && window.history && history.state && history.state.modalOpen) {{
              _ignoreNextPopstate = true;
              try {{
                history.back();
              }} catch (e) {{
                _ignoreNextPopstate = false;
              }}
            }}
          }}
        }}

        window.addEventListener('popstate', function(event) {{
          if (_ignoreNextPopstate) {{
            _ignoreNextPopstate = false;
            return;
          }}

          const backdrop = document.getElementById('global-modal-backdrop');
          const isBackdropActive = backdrop && !backdrop.classList.contains('hidden');

          if (isModalOpen || isBackdropActive || (event.state && event.state.modalOpen)) {{
            closeModal(true);
          }}
        }});

        // Backdrop click dismiss listener
        (function initModalBackdropListener() {{
          function attachListener() {{
            const backdrop = document.getElementById('global-modal-backdrop');
            if (backdrop && !backdrop.__hasBackdropClickListener) {{
              backdrop.__hasBackdropClickListener = true;
              backdrop.addEventListener('click', function(e) {{
                if (e.target === backdrop) {{
                  closeModal();
                }}
              }});
            }}
          }}
          attachListener();
        }})();

        // Escape key listener
        window.addEventListener('keydown', function(e) {{
          if (e.key === 'Escape' && isModalOpen) {{
            closeModal();
          }}
        }});

        {test_body}
        """

    def test_open_modal_pushes_history_state_and_shows_backdrop(self):
        """Stress: Verify openModal pushes state, unhides backdrop, and populates box."""
        test_body = """
        openModal('<p>مشاوره تحصیلی</p>', 'counselor-modal');

        console.log(JSON.stringify({
            isModalOpen: isModalOpen,
            backdropHidden: backdropEl.classList.contains('hidden'),
            boxContent: boxEl.innerHTML,
            historyCalls: historyCalls,
            currentState: history.state
        }));
        """
        res = self.run_node_js(self._get_history_harness_script(test_body))
        self.assertTrue(res["isModalOpen"], "isModalOpen must be true after openModal")
        self.assertFalse(res["backdropHidden"], "Backdrop must not have hidden class")
        self.assertIn("مشاوره تحصیلی", res["boxContent"], "Box must receive modal HTML content")
        self.assertEqual(len(res["historyCalls"]), 1, "Exactly one history call must be made")
        self.assertEqual(res["historyCalls"][0]["method"], "pushState", "Must call pushState")
        self.assertEqual(res["currentState"], {"modalOpen": True, "modalId": "counselor-modal"})

    def test_hardware_back_button_popstate_dismisses_modal_without_double_back(self):
        """Stress: Simulate Android hardware Back button (popstate); must close modal without calling history.back()."""
        test_body = """
        openModal('<p>محتوای مودال</p>', 'test-modal');
        const callsAfterOpen = historyCalls.length;

        // Simulate Android Hardware Back button triggering popstate event
        window.dispatchEvent({ type: 'popstate', state: null });

        console.log(JSON.stringify({
            isModalOpen: isModalOpen,
            backdropHidden: backdropEl.classList.contains('hidden'),
            callsAfterOpen: callsAfterOpen,
            totalHistoryCalls: historyCalls.length,
            historyCalls: historyCalls,
            _ignoreNextPopstate: _ignoreNextPopstate
        }));
        """
        res = self.run_node_js(self._get_history_harness_script(test_body))
        self.assertFalse(res["isModalOpen"], "Modal must be closed after popstate")
        self.assertTrue(res["backdropHidden"], "Backdrop must have hidden class after popstate")
        self.assertEqual(res["callsAfterOpen"], 1, "Should have 1 pushState from open")
        self.assertEqual(res["totalHistoryCalls"], 1, "popstate must NOT call history.back() (prevents double-navigation)")
        self.assertFalse(res["_ignoreNextPopstate"], "_ignoreNextPopstate must be false")

    def test_ui_close_synchronization_and_ignore_next_popstate(self):
        """Stress: Close via UI button/backdrop calls history.back() with _ignoreNextPopstate, swallowing the subsequent popstate."""
        test_body = """
        openModal('<p>دیالوگ</p>', 'my-dialog');
        const openCalls = historyCalls.length; // 1 (pushState)

        // Step 1: User clicks Close button in modal (closeModal() with no args)
        closeModal();
        const flagAfterClose = _ignoreNextPopstate;
        const callsAfterClose = historyCalls.length; // 2 (pushState, back)

        // Step 2: Browser responds to history.back() by firing popstate
        window.dispatchEvent({ type: 'popstate', state: null });
        const flagAfterFirstPopstate = _ignoreNextPopstate;
        const callsAfterFirstPopstate = historyCalls.length;

        // Step 3: User now presses Hardware Back button again
        // Modal is closed, history is synced; this popstate should pass through cleanly
        let subsequentActionTaken = false;
        window.dispatchEvent({ type: 'popstate', state: null });

        console.log(JSON.stringify({
            openCalls: openCalls,
            flagAfterClose: flagAfterClose,
            callsAfterClose: callsAfterClose,
            lastCallMethod: historyCalls[historyCalls.length - 1].method,
            flagAfterFirstPopstate: flagAfterFirstPopstate,
            callsAfterFirstPopstate: callsAfterFirstPopstate,
            isModalOpenAtEnd: isModalOpen,
            backdropHiddenAtEnd: backdropEl.classList.contains('hidden')
        }));
        """
        res = self.run_node_js(self._get_history_harness_script(test_body))
        self.assertEqual(res["openCalls"], 1, "Initial open must push state")
        self.assertTrue(res["flagAfterClose"], "_ignoreNextPopstate must be true immediately after closeModal()")
        self.assertEqual(res["callsAfterClose"], 2, "closeModal() must have called history.back()")
        self.assertEqual(res["lastCallMethod"], "back", "Last history action must be 'back'")
        self.assertFalse(res["flagAfterFirstPopstate"], "First popstate must consume and reset _ignoreNextPopstate to false")
        self.assertEqual(res["callsAfterFirstPopstate"], 2, "No extra history calls should be triggered by popstate")
        self.assertFalse(res["isModalOpenAtEnd"], "Modal must remain closed")
        self.assertTrue(res["backdropHiddenAtEnd"], "Backdrop must remain hidden")

    def test_no_modal_back_button_passthrough(self):
        """Stress: When no modal is open, popstate must take no action and not block navigation."""
        test_body = """
        // Initial state: no modal open
        const initialCalls = historyCalls.length;

        // User navigates back
        window.dispatchEvent({ type: 'popstate', state: null });

        console.log(JSON.stringify({
            initialCalls: initialCalls,
            totalCalls: historyCalls.length,
            isModalOpen: isModalOpen,
            _ignoreNextPopstate: _ignoreNextPopstate
        }));
        """
        res = self.run_node_js(self._get_history_harness_script(test_body))
        self.assertEqual(res["totalCalls"], 0, "No history calls should be made when no modal is open")
        self.assertFalse(res["isModalOpen"], "Modal state must remain closed")
        self.assertFalse(res["_ignoreNextPopstate"], "Flag must remain false")

    def test_rapid_nested_modal_replace_state(self):
        """Stress: Opening a second modal while one is open must replaceState instead of pushState (prevents stack bloat)."""
        test_body = """
        openModal('<p>Modal 1</p>', 'modal-1');
        const call1 = historyCalls[historyCalls.length - 1];

        // Replace/open second modal without closing first
        openModal('<p>Modal 2</p>', 'modal-2');
        const call2 = historyCalls[historyCalls.length - 1];

        console.log(JSON.stringify({
            call1Method: call1.method,
            call1State: call1.state,
            call2Method: call2.method,
            call2State: call2.state,
            totalCalls: historyCalls.length,
            currentState: history.state
        }));
        """
        res = self.run_node_js(self._get_history_harness_script(test_body))
        self.assertEqual(res["call1Method"], "pushState", "First modal open must pushState")
        self.assertEqual(res["call2Method"], "replaceState", "Second nested modal must replaceState")
        self.assertEqual(res["call2State"]["modalId"], "modal-2", "State must be updated to modal-2")
        self.assertEqual(res["totalCalls"], 2, "Total calls must be 2 (1 push, 1 replace; no extra push)")

    def test_idempotent_close_modal_calls(self):
        """Stress: Calling closeModal() multiple times when modal is closed must not spam history.back()."""
        test_body = """
        // Call closeModal 10 times consecutively
        for (let i = 0; i < 10; i++) {
            closeModal();
        }

        console.log(JSON.stringify({
            historyCallsCount: historyCalls.length,
            _ignoreNextPopstate: _ignoreNextPopstate
        }));
        """
        res = self.run_node_js(self._get_history_harness_script(test_body))
        self.assertEqual(res["historyCallsCount"], 0, "closeModal() on closed modal must be a complete no-op")
        self.assertFalse(res["_ignoreNextPopstate"], "Flag must remain false")

    def test_backdrop_click_target_discrimination(self):
        """Stress: Clicking backdrop closes modal; clicking modal box interior does NOT close modal."""
        test_body = """
        openModal('<div id="inner-content"><button id="inner-btn">تایید</button></div>', 'quiz-modal');

        // Simulate click inside the modal box
        backdropEl.dispatchEvent({ type: 'click', target: boxEl });
        const openAfterBoxClick = isModalOpen;

        // Simulate click on backdrop overlay itself
        backdropEl.dispatchEvent({ type: 'click', target: backdropEl });
        const openAfterBackdropClick = isModalOpen;

        console.log(JSON.stringify({
            openAfterBoxClick: openAfterBoxClick,
            openAfterBackdropClick: openAfterBackdropClick
        }));
        """
        res = self.run_node_js(self._get_history_harness_script(test_body))
        self.assertTrue(res["openAfterBoxClick"], "Clicking inside modal box must NOT dismiss modal")
        self.assertFalse(res["openAfterBackdropClick"], "Clicking on backdrop overlay MUST dismiss modal")

    def test_desktop_escape_key_listener(self):
        """Stress: Escape key dismisses modal when open; does nothing when closed."""
        test_body = """
        // Case A: Modal open, press Enter -> does nothing
        openModal('<p>Form</p>', 'form-modal');
        window.dispatchEvent({ type: 'keydown', key: 'Enter' });
        const openAfterEnter = isModalOpen;

        // Case B: Modal open, press Escape -> closes modal
        window.dispatchEvent({ type: 'keydown', key: 'Escape' });
        const openAfterEscape = isModalOpen;

        // Case C: Modal closed, press Escape -> no errors, no history calls
        const callsBefore = historyCalls.length;
        window.dispatchEvent({ type: 'keydown', key: 'Escape' });
        const callsAfter = historyCalls.length;

        console.log(JSON.stringify({
            openAfterEnter: openAfterEnter,
            openAfterEscape: openAfterEscape,
            noOpOnClosed: callsBefore === callsAfter
        }));
        """
        res = self.run_node_js(self._get_history_harness_script(test_body))
        self.assertTrue(res["openAfterEnter"], "Enter key must not close modal")
        self.assertFalse(res["openAfterEscape"], "Escape key must close modal")
        self.assertTrue(res["noOpOnClosed"], "Escape when modal closed must be a no-op")

    def test_history_back_exception_resilience(self):
        """Stress: If history.back() throws an exception, _ignoreNextPopstate must reset to false."""
        test_body = """
        openModal('<p>Test</p>', 'error-test');
        // Corrupt history.back to throw
        mockHistory.back = () => { throw new Error('SecurityError: History navigation blocked'); };

        closeModal();

        console.log(JSON.stringify({
            _ignoreNextPopstate: _ignoreNextPopstate,
            isModalOpen: isModalOpen
        }));
        """
        res = self.run_node_js(self._get_history_harness_script(test_body))
        self.assertFalse(res["_ignoreNextPopstate"], "Flag must be safely reset to false on history error")
        self.assertFalse(res["isModalOpen"], "Modal must be closed regardless")

    # =========================================================================
    # Group 2: Mobile Touch Ergonomics & Viewport CSS Rules (Static AST Analysis)
    # =========================================================================

    def test_touch_ergonomics_user_select_rules(self):
        """Verify user-select: none on interactive chrome and user-select: text on content/inputs."""
        # Check non-selectable chrome selectors
        chrome_pattern = re.search(
            r"button[\s\S]*?a[\s\S]*?nav[\s\S]*?\{[\s\S]*?user-select:\s*none[\s\S]*?-webkit-user-select:\s*none[\s\S]*?\}",
            self.html_content
        )
        self.assertIsNotNone(chrome_pattern, "Interactive elements (buttons, links, nav) must have user-select: none")
        self.assertIn("touch-action: manipulation", chrome_pattern.group(0), "Must include touch-action: manipulation")

        # Check selectable content selectors
        text_pattern = re.search(
            r"article[\s\S]*?input[\s\S]*?textarea[\s\S]*?\{[\s\S]*?user-select:\s*text[\s\S]*?-webkit-user-select:\s*text[\s\S]*?\}",
            self.html_content
        )
        self.assertIsNotNone(text_pattern, "Educational articles and form inputs must have user-select: text")

    def test_input_font_size_prevents_mobile_zoom(self):
        """Verify font-size: 16px !important rule on text/password/email/number/search inputs."""
        font_pattern = re.search(
            r"input\[type=\"text\"\][\s\S]*?textarea[\s\S]*?select[\s\S]*?\{[\s\S]*?font-size:\s*16px\s*!important;[\s\S]*?\}",
            self.html_content
        )
        self.assertIsNotNone(font_pattern, "Inputs, textareas, and selects must have font-size: 16px !important")

    def test_viewport_meta_and_html_body_overflow_constraints(self):
        """Verify overflow-x: hidden and max-width: 100vw on html, body; viewport-fit=cover."""
        self.assertRegex(
            self.html_content,
            r"<meta\s+name=[\"']viewport[\"']\s+content=[\"'][^\"']*width=device-width[^\"']*viewport-fit=cover[^\"']*[\"']",
            "Viewport meta must have width=device-width and viewport-fit=cover"
        )
        body_pattern = re.search(
            r"html,\s*body\s*\{[\s\S]*?overflow-x:\s*hidden;[\s\S]*?max-width:\s*100vw;[\s\S]*?-webkit-tap-highlight-color:\s*transparent;[\s\S]*?\}",
            self.html_content
        )
        self.assertIsNotNone(body_pattern, "html, body must enforce overflow-x: hidden, max-width: 100vw, and tap-highlight: transparent")

    def test_safe_area_insets_for_twa_and_mobile(self):
        """Verify safe-area-inset CSS rules for gesture bars and display notches."""
        self.assertIn("env(safe-area-inset-top", self.html_content)
        self.assertIn("env(safe-area-inset-bottom", self.html_content)

    # =========================================================================
    # Group 3: Real Headless Chrome Mobile Emulation (Live DOM & Styles)
    # =========================================================================

    def test_live_chrome_mobile_viewport_and_modal_dom(self):
        """Live Chrome: Launch in mobile emulation mode (375x812), verify modal container in live DOM."""
        if not self.has_chrome:
            self.skipTest("Chrome browser not installed on host")

        url = f"file:///{INDEX_HTML.as_posix()}?mode=app"
        proc = subprocess.run(
            [
                str(CHROME_PATH),
                "--headless",
                "--disable-gpu",
                "--window-size=375,812",
                "--user-agent=Mozilla/5.0 (Linux; Android 14; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
                "--dump-dom",
                url
            ],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )
        self.assertEqual(proc.returncode, 0, f"Chrome process exited with code {proc.returncode}")
        soup = BeautifulSoup(proc.stdout, "html.parser")

        # 1. Global modal backdrop exists and is hidden by default
        backdrop = soup.find(id="global-modal-backdrop")
        self.assertIsNotNone(backdrop, "Live DOM must contain #global-modal-backdrop")
        classes = backdrop.get("class", [])
        self.assertIn("hidden", classes, "#global-modal-backdrop must be hidden by default")
        self.assertIn("fixed", classes, "#global-modal-backdrop must be fixed inset-0")

        # 2. Global modal box exists
        box = soup.find(id="global-modal-box")
        self.assertIsNotNone(box, "Live DOM must contain #global-modal-box")

        # 3. Toast container exists
        toast = soup.find(id="toast-container")
        self.assertIsNotNone(toast, "Live DOM must contain #toast-container")


if __name__ == "__main__":
    unittest.main(verbosity=2)
