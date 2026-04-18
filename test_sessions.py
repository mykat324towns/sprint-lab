"""
Sprint Lab — 3-session Playwright test run (Python)
Sessions: strong (Day1), early-stop (bad sleep), acceptable (Day1 + rep-delete path)
Checks: UI flow, data persistence, analysis logic, plan generation, edge cases
"""
import json
import sys
from playwright.sync_api import sync_playwright, Dialog

URL = "http://localhost:3001"
FINDINGS = []


def log(category, severity, msg, detail=""):
    entry = {"category": category, "severity": severity, "msg": msg, "detail": detail}
    FINDINGS.append(entry)
    icon = "X" if severity == "ERROR" else "!" if severity == "WARN" else "+"
    suffix = f" -- {detail}" if detail else ""
    line = f"  [{icon} {severity}] [{category}] {msg}{suffix}"
    sys.stdout.buffer.write((line + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()


def ok(cat, msg):       log(cat, "OK",    msg)
def warn(cat, msg, d=""):  log(cat, "WARN", msg, d)
def err(cat, msg, d=""):   log(cat, "ERROR", msg, d)


# ── helpers ──────────────────────────────────────────────────────────────────
def set_slider(page, el_id, value):
    page.evaluate(
        """([id, v]) => {
            const el = document.getElementById(id);
            if (!el) throw new Error('slider not found: ' + id);
            el.value = v;
            el.dispatchEvent(new Event('input', {bubbles:true}));
        }""",
        [el_id, str(value)]
    )


def get_storage(page):
    raw = page.evaluate("() => localStorage.getItem('sprintlab_v1')")
    return json.loads(raw) if raw else None


def clear_storage(page):
    page.evaluate("() => localStorage.clear()")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(600)


def go_tab(page, tab):
    page.evaluate(f"() => Nav.goTo('{tab}')")
    page.wait_for_timeout(300)


def reset_wizard(page):
    step = page.evaluate("() => State.wizard.step")
    if step != 1:
        page.evaluate("""() => {
            State.wizard.step = 1;
            State.wizard.session = {readiness:{}, sprint:{reps:[]}, lift:{exercises:[]}, accessories:[], summary:{}};
            State.wizard.stopTriggered = false;
            State.wizard.repCount = 0;
            Wizard.init();
            Wizard.showStep(1);
        }""")
        page.wait_for_timeout(300)


def add_rep(page, quality, ease, rhythm, confidence, notes=""):
    # Use JS click to avoid visibility issues (btn-add-rep may be hidden due to bug in resetRepState)
    page.evaluate("() => document.getElementById('btn-add-rep').click()")
    page.wait_for_timeout(200)
    n = page.evaluate("() => State.wizard.repCount")
    base = f"rep{n}-"
    set_slider(page, base + "quality", quality)
    set_slider(page, base + "ease", ease)
    set_slider(page, base + "rhythm", rhythm)
    set_slider(page, base + "confidence", confidence)
    if notes:
        page.fill(f"#{base}notes", notes)
    return n


# ── Session 1: Strong Day 1, high readiness, 5 clean reps ─────────────────────
def session1(page):
    sys.stdout.buffer.write(b"\n=== SESSION 1: Strong Day 1 (high readiness, 5 clean reps) ===\n"); sys.stdout.buffer.flush()

    # Step 1 should be active
    if page.is_visible("#step-1.active"):
        ok("wizard", "Step 1 active on load")
    else:
        err("wizard", "Step 1 not active on load")

    set_slider(page, "r-legfresh", 9)
    set_slider(page, "r-genfresh", 8)
    set_slider(page, "r-energy", 9)

    leg_val = page.query_selector("#r-legfresh-val").inner_text()
    if leg_val == "9 / 10":
        ok("sliders", "Slider display updates correctly")
    else:
        err("sliders", "Slider display mismatch", f"got '{leg_val}'")

    no_active = page.eval_on_selector("#sleep-no", "el => el.classList.contains('active')")
    if no_active:
        ok("sleep-toggle", "Bad sleep default = No")
    else:
        err("sleep-toggle", "Bad sleep default not No")

    page.fill("#r-notes", "Legs feel bouncy, mentally sharp")

    # Step 1 → 2
    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(300)
    if page.is_visible("#step-2.active"):
        ok("wizard", "Moved to step 2")
    else:
        err("wizard", "Failed to move to step 2")

    # Try advancing step 2 without day type — should alert
    dialogs = []
    def handle_dialog(d: Dialog):
        dialogs.append(d.message)
        d.accept()
    page.once("dialog", handle_dialog)
    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(400)
    still_step2 = page.evaluate("() => State.wizard.step === 2")
    if still_step2:
        ok("validation", "Day type required -- blocked correctly")
    else:
        warn("validation", "Day type validation may not work")

    page.click("#day1-btn")
    page.wait_for_timeout(100)
    if page.eval_on_selector("#day1-btn", "el => el.classList.contains('active')"):
        ok("day-type", "Day 1 selected")
    else:
        err("day-type", "Day 1 not active after click")

    page.fill("#s-fly", "15")
    page.fill("#s-build", "30")
    page.fill("#s-floor", "3")
    page.fill("#s-ceiling", "5")

    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(300)
    if page.is_visible("#step-3.active"):
        ok("wizard", "Moved to step 3")
    else:
        err("wizard", "Failed to move to step 3")

    # Try advancing step 3 with 0 reps
    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(200)
    if page.evaluate("() => State.wizard.step === 3"):
        ok("validation", "Zero-rep guard works on step 3")
    else:
        err("validation", "Zero-rep guard missing on step 3")

    # Add 5 reps
    reps = [
        (8, 8, 8, 8, ""),
        (9, 8, 9, 9, "Felt fast and tall"),
        (8, 8, 8, 8, ""),
        (9, 9, 9, 9, "Best rep"),
        (8, 8, 8, 8, ""),
    ]
    for q, e, r, c, n in reps:
        add_rep(page, q, e, r, c, n)

    counter = page.query_selector("#rep-counter").inner_text()
    if "at ceiling" in counter:
        ok("rep-counter", f'Counter shows "at ceiling" at 5 reps')
    else:
        warn("rep-counter", "Counter text unexpected", counter)

    btn_hidden = page.eval_on_selector("#btn-add-rep", "el => el.style.display === 'none'")
    if btn_hidden:
        ok("ceiling-guard", "Add Rep hidden at ceiling")
    else:
        err("ceiling-guard", "Add Rep still visible at ceiling")

    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(500)

    if page.is_visible("#step-4.active"):
        ok("wizard", "Moved to step 4 (Lift)")
    else:
        err("wizard", "Failed to move to step 4")

    # Prescription card
    if page.query_selector("#step4-prescription-card .rx-card"):
        ok("prescription-card", "Prescription card rendered on step 4")
    else:
        warn("prescription-card", "Prescription card not found")

    # Accessory dropdowns
    if page.query_selector("#acc-pick-1"):
        ok("accessory-ui", "Accessory pick dropdowns rendered")
    else:
        err("accessory-ui", "Accessory pick dropdowns missing")

    # Lift rows
    rows = page.query_selector_all("#lift-rows-container .lift-row")
    if len(rows) >= 2:
        ok("lift-defaults", f"Lift defaults populated ({len(rows)} rows)")
    else:
        warn("lift-defaults", f"Lift defaults sparse: {len(rows)} rows")

    page.select_option("#lift-verdict", "supportive")
    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(300)

    if page.is_visible("#step-5.active"):
        ok("wizard", "Moved to step 5 (Summary)")
    else:
        err("wizard", "Failed to move to step 5")

    page.fill("#sum-best", "Reps 2 and 4 — really tall and elastic")
    page.fill("#sum-break", "None")
    page.fill("#sum-notes", "Dry track, perfect conditions")

    page.once("dialog", lambda d: d.accept())
    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(1500)

    if page.is_visible("#tab-analyzer.active"):
        ok("session-submit", "Session 1 saved, redirected to analyzer")
    else:
        err("session-submit", "Not redirected to analyzer after save")

    state = get_storage(page)
    sessions = state.get("sessions", []) if state else []
    # 3 sample + 1 new
    if len(sessions) == 4:
        ok("storage", "Session 1 persisted (4 total)")
    else:
        warn("storage", f"Unexpected session count: {len(sessions)}")

    s1 = sessions[-1] if sessions else {}
    reps_saved = s1.get("sprint", {}).get("reps", [])
    if len(reps_saved) == 5:
        ok("data-integrity", "Session 1: 5 reps saved")
    else:
        err("data-integrity", f"Session 1 reps: {len(reps_saved)}")

    verdict = s1.get("analysis", {}).get("sessionVerdict")
    if verdict == "strong":
        ok("analysis-logic", "Session 1 verdict = strong")
    else:
        warn("analysis-logic", f"Session 1 verdict = {verdict} (expected strong)")

    return s1


# ── Session 2: Early-stop, bad sleep, low readiness ────────────────────────────
def session2(page):
    sys.stdout.buffer.write(b"\n=== SESSION 2: Early-stop (bad sleep, forced reps) ===\n"); sys.stdout.buffer.flush()
    go_tab(page, "log")
    page.wait_for_timeout(300)
    reset_wizard(page)

    # Bad sleep ON
    page.click("#sleep-yes")
    page.wait_for_timeout(100)
    if page.eval_on_selector("#sleep-yes", "el => el.classList.contains('active')"):
        ok("sleep-toggle", "Sleep Yes toggle active")
    else:
        err("sleep-toggle", "Sleep Yes toggle not active")

    set_slider(page, "r-legfresh", 3)
    set_slider(page, "r-genfresh", 4)
    set_slider(page, "r-energy", 3)
    page.fill("#r-notes", "Poor sleep, heavy legs all morning")

    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(300)

    page.click("#day2-btn")
    page.fill("#s-fly", "15")
    page.fill("#s-floor", "3")
    page.fill("#s-ceiling", "5")

    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(300)

    add_rep(page, 5, 4, 5, 5, "")
    add_rep(page, 4, 3, 4, 4, "Forced, muscular feel")
    add_rep(page, 3, 3, 3, 3, "Forced stop")

    # Trigger stop
    page.click("#btn-stop")
    page.wait_for_timeout(300)

    if page.is_visible("#stop-status"):
        ok("stop-trigger", "Stop status banner visible")
    else:
        err("stop-trigger", "Stop status banner not visible")

    btn_disabled = page.eval_on_selector("#btn-stop", "el => el.disabled")
    if btn_disabled:
        ok("stop-trigger", "Stop button disabled after trigger")
    else:
        err("stop-trigger", "Stop button still enabled after trigger")

    add_btn_hidden = page.eval_on_selector("#btn-add-rep", "el => el.style.display === 'none'")
    if add_btn_hidden:
        ok("stop-trigger", "Add Rep hidden after stop")
    else:
        err("stop-trigger", "Add Rep visible after stop")

    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(400)

    page.select_option("#lift-verdict", "neutral")
    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(300)

    page.fill("#sum-best", "Showed up")
    page.fill("#sum-break", "Rep 2 onwards — forced and muscular")

    page.once("dialog", lambda d: d.accept())
    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(1500)

    state = get_storage(page)
    sessions = state.get("sessions", []) if state else []
    s2 = sessions[-1] if sessions else {}

    stop_saved = s2.get("sprint", {}).get("stopTriggered")
    if stop_saved is True:
        ok("data-integrity", "stopTriggered=true saved")
    else:
        err("data-integrity", f"stopTriggered={stop_saved}")

    reps2 = s2.get("sprint", {}).get("reps", [])
    if len(reps2) == 3:
        ok("data-integrity", "Session 2: 3 reps saved")
    else:
        warn("data-integrity", f"Session 2 reps: {len(reps2)}")

    v2 = s2.get("analysis", {}).get("sessionVerdict")
    if v2 in ("degraded", "abort"):
        ok("analysis-logic", f"Session 2 verdict = {v2}")
    else:
        err("analysis-logic", f"Session 2 verdict = {v2} (expected degraded/abort)")

    pd2 = s2.get("analysis", {}).get("progressionDecision", "")
    if pd2.startswith("regress"):
        ok("progression-logic", f"Session 2 progression = {pd2}")
    else:
        err("progression-logic", f"Session 2 progression = {pd2} (expected regress_*)")

    # readiness score with bad sleep: avg(3,4,3) - 1.5 = 2.17
    rs2 = s2.get("analysis", {}).get("readinessScore")
    if rs2 is not None and rs2 < 5:
        ok("readiness-calc", f"Bad sleep session readinessScore={rs2} (correctly low)")
    else:
        warn("readiness-calc", f"readinessScore={rs2} for bad-sleep session (should be <5)")

    return s2


# ── Session 3: Acceptable Day 1 + rep delete test ─────────────────────────────
def session3(page):
    sys.stdout.buffer.write(b"\n=== SESSION 3: Acceptable Day 1 (with rep delete test) ===\n"); sys.stdout.buffer.flush()
    go_tab(page, "log")
    page.wait_for_timeout(300)
    reset_wizard(page)

    set_slider(page, "r-legfresh", 6)
    set_slider(page, "r-genfresh", 6)
    set_slider(page, "r-energy", 7)

    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(300)

    page.click("#day1-btn")
    page.fill("#s-fly", "15")
    page.fill("#s-floor", "3")
    page.fill("#s-ceiling", "5")
    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(300)

    # Add 3 reps then delete the middle
    add_rep(page, 7, 6, 7, 7, "")
    add_rep(page, 6, 5, 6, 6, "Slightly flat")
    add_rep(page, 7, 7, 7, 7, "")

    # Delete rep 2
    rep2 = page.query_selector("#rep-card-2")
    if rep2:
        del_btn = rep2.query_selector(".rep-delete")
        if del_btn:
            del_btn.click()
            page.wait_for_timeout(200)
            ok("rep-delete", "Rep 2 deleted")
        else:
            err("rep-delete", "Delete button not found on rep-card-2")
    else:
        err("rep-delete", "rep-card-2 not found")

    count_after = page.evaluate("() => State.wizard.repCount")
    if count_after == 2:
        ok("rep-delete", f"repCount = 2 after deletion")
    else:
        err("rep-delete", f"repCount = {count_after} after deletion (expected 2)")

    # Check card renumbering
    card_ids = page.evaluate(
        "() => [...document.querySelectorAll('.rep-card')].map(c => c.id)"
    )
    if card_ids == ["rep-card-1", "rep-card-2"]:
        ok("rep-renumber", "Cards correctly renumbered: rep-card-1, rep-card-2")
    else:
        err("rep-renumber", f"Renumbering wrong: {card_ids}")

    # Slider IDs updated — critical for data capture
    slider_ok = page.evaluate("() => !!document.getElementById('rep2-quality')")
    if slider_ok:
        ok("rep-renumber", "rep2-quality slider exists after renumber")
    else:
        err("rep-renumber", "rep2-quality missing after renumber — data capture broken")

    # Add rep back to get to 3
    add_rep(page, 7, 7, 7, 7, "")

    final_count = page.evaluate("() => State.wizard.repCount")
    if final_count == 3:
        ok("rep-add-after-delete", "Can add rep after delete (count=3)")
    else:
        err("rep-add-after-delete", f"Unexpected count: {final_count}")

    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(400)

    page.select_option("#lift-verdict", "neutral")
    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(300)

    page.fill("#sum-best", "Held together after tough session yesterday")
    page.fill("#sum-break", "Rep 2 slightly flat")

    page.once("dialog", lambda d: d.accept())
    page.evaluate("() => document.querySelector('.wizard-step.active .wizard-nav .btn-primary').click()")
    page.wait_for_timeout(1500)

    state = get_storage(page)
    sessions = state.get("sessions", []) if state else []
    s3 = sessions[-1] if sessions else {}

    reps3 = s3.get("sprint", {}).get("reps", [])
    if len(reps3) == 3:
        ok("data-integrity", "Session 3: 3 reps saved")
    else:
        err("data-integrity", f"Session 3 reps: {len(reps3)} (expected 3)")

    all_valid = all(1 <= r.get("quality", 0) <= 10 for r in reps3)
    if all_valid:
        ok("data-integrity", "All rep scores in session 3 valid (1-10)")
    else:
        err("data-integrity", "Rep scores out of range in session 3")

    v3 = s3.get("analysis", {}).get("sessionVerdict")
    if v3 == "acceptable":
        ok("analysis-logic", "Session 3 verdict = acceptable")
    else:
        warn("analysis-logic", f"Session 3 verdict = {v3} (expected acceptable)")

    return s3


# ── Tab/navigation checks ─────────────────────────────────────────────────────
def tab_checks(page):
    sys.stdout.buffer.write(b"\n=== TAB / NAVIGATION CHECKS ===\n"); sys.stdout.buffer.flush()

    go_tab(page, "plan")
    page.wait_for_timeout(500)

    plan_card = page.query_selector("#plan-display .card")
    if plan_card:
        ok("plan-tab", "Plan tab renders a card")
    else:
        err("plan-tab", "Plan tab empty after 3 sessions")

    plan_text = page.eval_on_selector("#plan-display", "el => el.innerText")
    if "fly" in plan_text.lower() or "day" in plan_text.lower():
        ok("plan-tab", "Plan content contains fly/day info")
    else:
        warn("plan-tab", "Plan content missing fly/day", plan_text[:80])

    state = get_storage(page)
    plan = state.get("nextPlan") if state else None
    if plan:
        ok("plan-storage", "nextPlan in localStorage")
    else:
        err("plan-storage", "nextPlan missing from localStorage")

    if plan and plan.get("progressionDecision"):
        ok("plan-logic", f"progressionDecision = {plan['progressionDecision']}")
    else:
        err("plan-logic", "progressionDecision missing from plan")

    if plan:
        cr = plan.get("ceilingReps", 0)
        fly = plan.get("fly", 0)
        if 1 <= cr <= 6:
            ok("plan-constraints", f"ceilingReps={cr} within 1-6")
        else:
            warn("plan-constraints", f"ceilingReps={cr} outside expected range")
        if 10 <= fly <= 25:
            ok("plan-constraints", f"fly={fly}m within 10-25")
        else:
            err("plan-constraints", f"fly={fly}m outside 10-25")

        accs = plan.get("accessories", [])
        if len(accs) >= 2:
            ok("accessory-plan", f"Plan has {len(accs)} accessories")
        else:
            warn("accessory-plan", f"Plan has {len(accs)} accessories (expected ≥2)")

        cats = [a.get("category") for a in accs]
        if len(cats) == len(set(cats)):
            ok("accessory-dedup", "No duplicate categories in plan accessories")
        else:
            err("accessory-dedup", f"Duplicate categories: {cats}")

    # History tab
    go_tab(page, "history")
    page.wait_for_timeout(500)

    cards = page.query_selector_all("#session-cards .card, #session-cards [class*='session-card']")
    # The history renders into #session-cards — let's check there's content
    history_html = page.eval_on_selector("#session-cards", "el => el.innerHTML")
    if history_html and len(history_html) > 50:
        ok("history-tab", "History session cards rendered")
    else:
        warn("history-tab", "History may be empty or not rendered")

    if page.query_selector("#trend-chart"):
        ok("history-chart", "Trend chart canvas exists")
    else:
        err("history-chart", "Trend chart canvas missing")

    # Analyzer tab
    go_tab(page, "analyzer")
    page.wait_for_timeout(400)

    opts = page.query_selector_all("#analyzer-session-select option")
    if len(opts) >= 3:
        ok("analyzer-tab", f"Analyzer has {len(opts)} sessions")
    else:
        warn("analyzer-tab", f"Only {len(opts)} sessions in analyzer select")

    # Rules tab
    go_tab(page, "rules")
    page.wait_for_timeout(300)

    rules_html = page.eval_on_selector("#rules-content", "el => el.innerHTML")
    if rules_html and len(rules_html) > 100:
        ok("rules-tab", "Rules content rendered")
    else:
        err("rules-tab", "Rules content empty")

    # Data tab
    go_tab(page, "data")
    page.wait_for_timeout(200)
    export_btn = page.query_selector("button:has-text('Export JSON')")
    if export_btn:
        ok("data-tab", "Export JSON button present")
    else:
        err("data-tab", "Export JSON button missing")


# ── Logic / formula spot-checks ───────────────────────────────────────────────
def logic_checks(page):
    sys.stdout.buffer.write(b"\n=== LOGIC SPOT-CHECKS ===\n"); sys.stdout.buffer.flush()

    state = get_storage(page)
    sessions = state.get("sessions", []) if state else []
    s3 = sessions[-1] if len(sessions) >= 1 else {}
    s2 = sessions[-2] if len(sessions) >= 2 else {}

    # Readiness score: avg(6,6,7) = 6.33, no bad sleep
    rs3 = s3.get("analysis", {}).get("readinessScore")
    expected = (6 + 6 + 7) / 3
    if rs3 is not None and abs(rs3 - expected) < 0.5:
        ok("readiness-calc", f"readinessScore={rs3} ≈ {expected:.1f}")
    else:
        warn("readiness-calc", f"readinessScore={rs3} vs expected≈{expected:.1f}")

    # Session 2 (stop) should produce regress
    pd2 = s2.get("analysis", {}).get("progressionDecision", "")
    if pd2.startswith("regress"):
        ok("regression-after-stop", f"Stop session correctly regresses: {pd2}")
    else:
        err("regression-after-stop", f"Stop session decision = {pd2} (expected regress_*)")

    # BlockManager — at least one block
    blocks = state.get("settings", {}).get("accessoryBlocks", []) if state else []
    if blocks:
        ok("block-manager", f"{len(blocks)} accessory block(s)")
    else:
        warn("block-manager", "No accessory blocks — attachSession may not have run")

    open_block = next((b for b in blocks if b.get("status") == "open"), None)
    if open_block:
        ok("block-manager", f"Open block: {len(open_block.get('sessionIds',[]))} sessions")
    else:
        warn("block-manager", "No open block")

    # accessoryScores initialized
    scores = state.get("settings", {}).get("accessoryScores", {}) if state else {}
    if scores:
        ok("block-manager", f"accessoryScores for {len(scores)} exercises")
    else:
        err("block-manager", "accessoryScores not initialized")

    # Plan day type alternation
    plan = state.get("nextPlan") if state else None
    last_day = s3.get("dayType")
    expected_next = "day2" if last_day == "day1" else "day1"
    if plan and plan.get("dayType") == expected_next:
        ok("plan-day-alternation", f"Plan correctly → {plan['dayType']} after {last_day}")
    else:
        warn("plan-day-alternation",
             f"Plan dayType={plan.get('dayType') if plan else None}, expected {expected_next} after {last_day}")

    # Plan accessories match ACCESSORY_LIBRARY (no phantom IDs)
    if plan:
        lib_ids = page.evaluate(
            "() => Plan.ACCESSORY_LIBRARY.map(e => e.id)"
        )
        accs = plan.get("accessories", [])
        for a in accs:
            if a.get("id") in lib_ids:
                ok("accessory-ids", f"Accessory id '{a['id']}' is valid library entry")
            else:
                err("accessory-ids", f"Phantom accessory id '{a.get('id')}' not in library")

    # Session 1 analysis: 5 reps, all quality 8-9 → should be strong
    s1_sessions = [s for s in sessions if not s.get("sprint", {}).get("stopTriggered")]
    if s1_sessions:
        s1 = s1_sessions[0] if len(s1_sessions) == 1 else None
        # Find by reps count
        for s in sessions:
            if len(s.get("sprint", {}).get("reps", [])) == 5 and not s.get("sprint", {}).get("stopTriggered"):
                v = s.get("analysis", {}).get("sessionVerdict")
                if v == "strong":
                    ok("analysis-logic", "5-rep high-quality session = strong verdict")
                else:
                    warn("analysis-logic", f"5-rep high-quality session verdict = {v} (expected strong)")
                break

    # Pogo Hops always prepended in accessories
    for s in sessions[-3:]:
        accs = s.get("accessories", [])
        if accs and accs[0].get("id") == "pogo_hops":
            ok("accessory-prepend", f"Pogo Hops first in session accessories")
        elif accs:
            warn("accessory-prepend", f"Pogo Hops not first in accessories: {[a.get('id') for a in accs]}")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 480, "height": 900})
        page = ctx.new_page()

        # Log browser errors
        def on_console(msg):
            try:
                if msg.type == "error":
                    err("console", msg.text[:120])
            except Exception:
                pass
        def on_page_error(e):
            try:
                err("page-error", str(e)[:120])
            except Exception:
                pass
        page.on("console", on_console)
        page.on("pageerror", on_page_error)

        try:
            page.goto(URL, wait_until="domcontentloaded")
            page.wait_for_timeout(800)
            clear_storage(page)

            session1(page)
            session2(page)
            session3(page)
            tab_checks(page)
            logic_checks(page)

        except Exception as e:
            err("test-runner", f"Unexpected error: {e}")
        finally:
            browser.close()

    # ── Report ────────────────────────────────────────────────────────────────
    sys.stdout.buffer.write(("\n" + "=" * 60 + "\nFINDINGS REPORT\n" + "=" * 60 + "\n").encode("utf-8"))
    sys.stdout.buffer.flush()

    errors = [f for f in FINDINGS if f["severity"] == "ERROR"]
    warnings = [f for f in FINDINGS if f["severity"] == "WARN"]
    oks = [f for f in FINDINGS if f["severity"] == "OK"]

    sys.stdout.buffer.write(f"\n+ PASSED : {len(oks)}\n! WARNINGS: {len(warnings)}\nX ERRORS  : {len(errors)}\n".encode("utf-8"))
    sys.stdout.buffer.flush()

    def bprint(s):
        sys.stdout.buffer.write((s + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()

    if errors:
        bprint("\n--- ERRORS ---")
        for f in errors:
            bprint(f"  [{f['category']}] {f['msg']}" + (f" -- {f['detail']}" if f['detail'] else ""))

    if warnings:
        bprint("\n--- WARNINGS ---")
        for f in warnings:
            bprint(f"  [{f['category']}] {f['msg']}" + (f" -- {f['detail']}" if f['detail'] else ""))

    return len(errors), len(warnings)


if __name__ == "__main__":
    e, w = main()
    sys.exit(1 if e > 0 else 0)
