/**
 * Sprint Lab — 3-session Playwright test run
 * Tests: strong session, early-stop session, acceptable (Day 2) session
 * Checks: UI flow, data persistence, analysis correctness, plan generation, edge cases
 */
import { chromium } from 'playwright';

const URL = 'http://localhost:3001';
const FINDINGS = [];

function log(category, severity, msg, detail = '') {
  const entry = { category, severity, msg, detail };
  FINDINGS.push(entry);
  const icon = severity === 'ERROR' ? '✗' : severity === 'WARN' ? '⚠' : '✓';
  console.log(`  [${icon} ${severity}] [${category}] ${msg}${detail ? ' — ' + detail : ''}`);
}

function ok(category, msg) { log(category, 'OK', msg); }
function warn(category, msg, detail = '') { log(category, 'WARN', msg, detail); }
function err(category, msg, detail = '') { log(category, 'ERROR', msg, detail); }

// ── helpers ──────────────────────────────────────────────
async function setSlider(page, id, value) {
  await page.evaluate(({ id, value }) => {
    const el = document.getElementById(id);
    if (!el) throw new Error('Slider not found: ' + id);
    el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }, { id, value });
}

async function getStorageState(page) {
  return page.evaluate(() => {
    try { return JSON.parse(localStorage.getItem('sprintlab_v1') || 'null'); } catch { return null; }
  });
}

async function clearStorage(page) {
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);
}

async function clickNav(page, tab) {
  await page.evaluate((t) => Nav.goTo(t), tab);
  await page.waitForTimeout(300);
}

async function addRepCard(page, { quality, ease, rhythm, confidence, notes = '' }) {
  await page.click('#btn-add-rep');
  await page.waitForTimeout(200);

  // Find last rep-card to get rep number
  const repNum = await page.evaluate(() => State.wizard.repCount);
  const base = `rep${repNum}-`;

  await setSlider(page, base + 'quality', quality);
  await setSlider(page, base + 'ease', ease);
  await setSlider(page, base + 'rhythm', rhythm);
  await setSlider(page, base + 'confidence', confidence);

  if (notes) {
    await page.fill(`#${base}notes`, notes);
  }
  return repNum;
}

// ── Session 1: Strong session (Day 1, high readiness, 5 clean reps) ──────────
async function runSession1(page) {
  console.log('\n═══ SESSION 1: Strong Day 1 (high readiness, 5 clean reps) ═══');

  // Step 1: Readiness
  const step1Visible = await page.isVisible('#step-1.active');
  if (step1Visible) ok('wizard', 'Step 1 is active on load');
  else err('wizard', 'Step 1 not active on load');

  // Set sliders high
  await setSlider(page, 'r-legfresh', 9);
  await setSlider(page, 'r-genfresh', 8);
  await setSlider(page, 'r-energy', 9);

  // Verify slider values display
  const legVal = await page.$eval('#r-legfresh-val', el => el.textContent);
  if (legVal === '9 / 10') ok('readiness-sliders', 'Slider display updates correctly');
  else err('readiness-sliders', 'Slider display mismatch', `expected "9 / 10", got "${legVal}"`);

  // Bad sleep toggle — default should be No
  const noActive = await page.$eval('#sleep-no', el => el.classList.contains('active'));
  if (noActive) ok('sleep-toggle', 'Bad sleep default is No');
  else err('sleep-toggle', 'Bad sleep default is not No');

  await page.fill('#r-notes', 'Legs feel bouncy, mentally sharp');

  // Try going Next without selecting dayType — should work (it's step 2 that requires it)
  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(300);

  const step2Visible = await page.isVisible('#step-2.active');
  if (step2Visible) ok('wizard', 'Moved to step 2');
  else err('wizard', 'Failed to move to step 2');

  // Step 2: Sprint Setup — try advancing without dayType
  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(200);
  const alertFired = await page.evaluate(() => {
    // Check if still on step 2 (alert blocks progression)
    return State.wizard.step === 2;
  });
  if (alertFired) ok('validation', 'Day type required alert fires correctly');
  else warn('validation', 'Day type validation may not be working');

  // Dismiss alert if it appeared
  page.on('dialog', d => d.accept());

  // Now select Day 1
  await page.click('#day1-btn');
  await page.waitForTimeout(100);
  const day1Active = await page.$eval('#day1-btn', el => el.classList.contains('active'));
  if (day1Active) ok('day-type', 'Day 1 selected correctly');
  else err('day-type', 'Day 1 not marked active');

  // Set sprint params
  await page.fill('#s-fly', '15');
  await page.fill('#s-build', '30');
  await page.fill('#s-floor', '3');
  await page.fill('#s-ceiling', '5');

  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(300);

  const step3Visible = await page.isVisible('#step-3.active');
  if (step3Visible) ok('wizard', 'Moved to step 3');
  else err('wizard', 'Failed to move to step 3');

  // Step 3: Try advancing with 0 reps
  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(200);
  const blockedAt3 = await page.evaluate(() => State.wizard.step === 3);
  if (blockedAt3) ok('validation', 'Cannot advance step 3 with 0 reps');
  else err('validation', 'Step 3 zero-rep guard missing');

  // Add 5 clean reps
  const repData = [
    { quality: 8, ease: 8, rhythm: 8, confidence: 8 },
    { quality: 9, ease: 8, rhythm: 9, confidence: 9, notes: 'Felt fast and tall' },
    { quality: 8, ease: 8, rhythm: 8, confidence: 8 },
    { quality: 9, ease: 9, rhythm: 9, confidence: 9, notes: 'Best rep' },
    { quality: 8, ease: 8, rhythm: 8, confidence: 8 },
  ];
  for (const rep of repData) {
    await addRepCard(page, rep);
  }

  // Check rep counter text
  const counterText = await page.$eval('#rep-counter', el => el.textContent);
  if (counterText.includes('at ceiling')) ok('rep-counter', 'Counter shows "at ceiling" at 5 reps');
  else warn('rep-counter', 'Counter text unexpected at ceiling', counterText);

  // Check Add Rep button hidden at ceiling
  const addBtnHidden = await page.$eval('#btn-add-rep', el => el.style.display === 'none');
  if (addBtnHidden) ok('ceiling-guard', 'Add Rep button hidden at ceiling');
  else err('ceiling-guard', 'Add Rep button still visible at ceiling');

  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(400);

  const step4Visible = await page.isVisible('#step-4.active');
  if (step4Visible) ok('wizard', 'Moved to step 4 (Lift)');
  else err('wizard', 'Failed to move to step 4');

  // Check prescription card rendered
  const rxCard = await page.$('#step4-prescription-card .rx-card');
  if (rxCard) ok('prescription-card', 'Prescription card rendered on step 4');
  else warn('prescription-card', 'Prescription card not found on step 4');

  // Check accessory dropdowns rendered
  const pick1Exists = await page.$('#acc-pick-1');
  if (pick1Exists) ok('accessory-ui', 'Accessory pick dropdowns rendered');
  else err('accessory-ui', 'Accessory pick dropdowns missing');

  // Check lift defaults populated
  const liftRows = await page.$$('#lift-rows-container .lift-row');
  if (liftRows.length >= 2) ok('lift-defaults', `Lift defaults populated (${liftRows.length} rows)`);
  else warn('lift-defaults', 'Lift defaults may be missing', `${liftRows.length} rows`);

  // Fill in lift data
  await page.evaluate(() => {
    const rows = document.querySelectorAll('#lift-rows-container .lift-row');
    if (rows[0]) {
      rows[0].querySelectorAll('input[type="text"]')[0].value = 'Back Squat';
      rows[0].querySelectorAll('input[type="number"]')[0].value = 4;
      rows[0].querySelectorAll('input[type="number"]')[1].value = 4;
      rows[0].querySelectorAll('input[type="text"]')[1].value = '135lb';
    }
  });

  await page.selectOption('#lift-verdict', 'supportive');

  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(300);

  const step5Visible = await page.isVisible('#step-5.active');
  if (step5Visible) ok('wizard', 'Moved to step 5 (Summary)');
  else err('wizard', 'Failed to move to step 5');

  await page.fill('#sum-best', 'Reps 2 and 4 — really tall and elastic');
  await page.fill('#sum-break', 'None');
  await page.fill('#sum-notes', 'Dry track, perfect conditions');

  // Submit session
  page.once('dialog', d => d.accept()); // "Session saved!"
  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(1500);

  // Should be on analyzer tab now
  const analyzerActive = await page.isVisible('#tab-analyzer.active');
  if (analyzerActive) ok('session-submit', 'Session 1 saved, redirected to analyzer');
  else err('session-submit', 'Not redirected to analyzer after session 1 save');

  // Check analysis verdict
  const verdictText = await page.$eval('#analysis-results', el => el.innerText).catch(() => '');
  if (verdictText.includes('strong') || verdictText.includes('acceptable')) {
    ok('analysis', `Session 1 verdict rendered: ${verdictText.match(/strong|acceptable|degraded/)?.[0]}`);
  } else {
    warn('analysis', 'Verdict not found in analysis results');
  }

  // Verify session saved in storage
  const state = await getStorageState(page);
  const sessions = state?.sessions || [];
  // Sample sessions (3) + session 1 = 4
  if (sessions.length === 4) ok('storage', 'Session 1 persisted (4 total with samples)');
  else warn('storage', `Unexpected session count: ${sessions.length}`);

  const s1 = sessions[sessions.length - 1];
  if (s1?.sprint?.reps?.length === 5) ok('data-integrity', 'Session 1 has 5 reps saved');
  else err('data-integrity', `Session 1 reps wrong: ${s1?.sprint?.reps?.length}`);

  if (s1?.analysis?.sessionVerdict === 'strong') ok('analysis-logic', 'Session 1 verdict = strong');
  else warn('analysis-logic', `Session 1 verdict = ${s1?.analysis?.sessionVerdict} (expected strong)`);

  return s1;
}

// ── Session 2: Early-stop (bad sleep, forced reps, stop triggered) ────────────
async function runSession2(page) {
  console.log('\n═══ SESSION 2: Early-stop (bad sleep, forced, stop triggered) ═══');

  await clickNav(page, 'log');
  await page.waitForTimeout(300);

  // Reset wizard back to step 1
  const step = await page.evaluate(() => State.wizard.step);
  if (step !== 1) {
    // Force reset
    await page.evaluate(() => {
      State.wizard.step = 1;
      State.wizard.session = { readiness: {}, sprint: { reps: [] }, lift: { exercises: [] }, accessories: [], summary: {} };
      State.wizard.stopTriggered = false;
      State.wizard.repCount = 0;
      Wizard.init();
      Wizard.showStep(1);
    });
    await page.waitForTimeout(300);
  }

  // Step 1: Bad sleep, low readiness
  await page.click('#sleep-yes');
  await page.waitForTimeout(100);
  const yesActive = await page.$eval('#sleep-yes', el => el.classList.contains('active'));
  if (yesActive) ok('sleep-toggle', 'Sleep toggle switches to Yes');
  else err('sleep-toggle', 'Sleep yes toggle not active');

  await setSlider(page, 'r-legfresh', 3);
  await setSlider(page, 'r-genfresh', 4);
  await setSlider(page, 'r-energy', 3);
  await page.fill('#r-notes', 'Poor sleep, heavy legs all morning');

  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(300);

  // Step 2: Day 2 (plan should suggest day2 after day1)
  await page.click('#day2-btn');
  await page.fill('#s-fly', '15');
  await page.fill('#s-floor', '3');
  await page.fill('#s-ceiling', '5');
  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(300);

  // Step 3: Add 3 declining reps then stop
  await addRepCard(page, { quality: 5, ease: 4, rhythm: 5, confidence: 5 });
  await addRepCard(page, { quality: 4, ease: 3, rhythm: 4, confidence: 4, notes: 'Forced, muscular feel' });
  await addRepCard(page, { quality: 3, ease: 3, rhythm: 3, confidence: 3, notes: 'Forced stop' });

  // Trigger stop
  await page.click('#btn-stop');
  await page.waitForTimeout(300);

  // Check stop state
  const stopStatus = await page.isVisible('#stop-status');
  if (stopStatus) ok('stop-trigger', 'Stop status banner visible after triggering stop');
  else err('stop-trigger', 'Stop status banner not visible');

  const btnDisabled = await page.$eval('#btn-stop', el => el.disabled);
  if (btnDisabled) ok('stop-trigger', 'Stop button disabled after trigger');
  else err('stop-trigger', 'Stop button still enabled after trigger');

  const addBtnHidden = await page.$eval('#btn-add-rep', el => el.style.display === 'none');
  if (addBtnHidden) ok('stop-trigger', 'Add Rep hidden after stop triggered');
  else err('stop-trigger', 'Add Rep still visible after stop');

  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(400);

  // Step 4 — add minimal lift data
  await page.selectOption('#lift-verdict', 'neutral');
  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(300);

  // Step 5
  await page.fill('#sum-best', 'Showed up');
  await page.fill('#sum-break', 'Rep 2 onwards — forced and muscular');

  page.once('dialog', d => d.accept());
  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(1500);

  // Verify analysis on stopped session
  const state = await getStorageState(page);
  const sessions = state?.sessions || [];
  const s2 = sessions[sessions.length - 1];

  if (s2?.sprint?.stopTriggered === true) ok('data-integrity', 'Session 2 stopTriggered=true saved');
  else err('data-integrity', 'stopTriggered not saved correctly');

  if (s2?.sprint?.reps?.length === 3) ok('data-integrity', 'Session 2 has 3 reps saved');
  else warn('data-integrity', `Expected 3 reps, got ${s2?.sprint?.reps?.length}`);

  const v2 = s2?.analysis?.sessionVerdict;
  if (v2 === 'degraded' || v2 === 'abort') ok('analysis-logic', `Session 2 verdict = ${v2} (correct for stop+low scores)`);
  else err('analysis-logic', `Session 2 verdict = ${v2} (expected degraded or abort)`);

  const pd2 = s2?.analysis?.progressionDecision;
  if (pd2 === 'regress_reps' || pd2 === 'regress_fly') ok('progression-logic', `Session 2 progression = ${pd2} (correct after stop)`);
  else err('progression-logic', `Session 2 progression = ${pd2} (expected regress_reps)`);

  return s2;
}

// ── Session 3: Acceptable Day 1, delete-rep path, ceiling via +1 at floor ────
async function runSession3(page) {
  console.log('\n═══ SESSION 3: Acceptable Day 1 (with rep delete test) ═══');

  await clickNav(page, 'log');
  await page.waitForTimeout(300);

  // Reset wizard
  const step = await page.evaluate(() => State.wizard.step);
  if (step !== 1) {
    await page.evaluate(() => {
      State.wizard.step = 1;
      State.wizard.session = { readiness: {}, sprint: { reps: [] }, lift: { exercises: [] }, accessories: [], summary: {} };
      State.wizard.stopTriggered = false;
      State.wizard.repCount = 0;
      Wizard.init();
      Wizard.showStep(1);
    });
    await page.waitForTimeout(300);
  }

  // Step 1: Medium readiness
  await setSlider(page, 'r-legfresh', 6);
  await setSlider(page, 'r-genfresh', 6);
  await setSlider(page, 'r-energy', 7);

  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(300);

  // Step 2: Day 1
  await page.click('#day1-btn');
  await page.fill('#s-fly', '15');
  await page.fill('#s-floor', '3');
  await page.fill('#s-ceiling', '5');
  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(300);

  // Step 3: Add 3 reps, delete the middle one, then verify renumbering
  await addRepCard(page, { quality: 7, ease: 6, rhythm: 7, confidence: 7 });
  await addRepCard(page, { quality: 6, ease: 5, rhythm: 6, confidence: 6, notes: 'Slightly flat' });
  await addRepCard(page, { quality: 7, ease: 7, rhythm: 7, confidence: 7 });

  // Check rep counter at 3 (floor)
  const counterText = await page.$eval('#rep-counter', el => el.textContent);
  if (counterText.includes('at ceiling') || counterText.includes('2 more to ceiling')) {
    ok('rep-counter', 'Rep counter correct at 3 reps');
  }

  // Delete rep 2 (middle)
  const rep2Card = await page.$('#rep-card-2');
  if (rep2Card) {
    const deleteBtn = await rep2Card.$('.rep-delete');
    if (deleteBtn) {
      await deleteBtn.click();
      await page.waitForTimeout(200);
      ok('rep-delete', 'Rep 2 deleted');
    } else {
      err('rep-delete', 'Delete button not found on rep-card-2');
    }
  } else {
    err('rep-delete', 'rep-card-2 not found');
  }

  // After deletion, should have 2 reps
  const repCountAfterDelete = await page.evaluate(() => State.wizard.repCount);
  if (repCountAfterDelete === 2) ok('rep-delete', 'repCount = 2 after deletion');
  else err('rep-delete', `repCount = ${repCountAfterDelete} after deletion (expected 2)`);

  // Check that the remaining cards are numbered 1 and 2
  const cardIds = await page.evaluate(() =>
    [...document.querySelectorAll('.rep-card')].map(c => c.id)
  );
  if (cardIds[0] === 'rep-card-1' && cardIds[1] === 'rep-card-2') {
    ok('rep-renumber', 'Cards correctly renumbered after delete: rep-card-1, rep-card-2');
  } else {
    err('rep-renumber', `Renumbering incorrect: ${cardIds}`);
  }

  // Check slider IDs after renumber — critical for data capture
  const slider1Exists = await page.$('#rep2-quality');
  if (slider1Exists) ok('rep-renumber', 'Slider IDs updated after renumber (rep2-quality exists)');
  else err('rep-renumber', 'Slider IDs broken after renumber — rep2-quality missing');

  // Add one more rep to bring back to 3
  await addRepCard(page, { quality: 7, ease: 7, rhythm: 7, confidence: 7 });

  const finalCount = await page.evaluate(() => State.wizard.repCount);
  if (finalCount === 3) ok('rep-add-after-delete', 'Can add rep after delete (count = 3)');
  else err('rep-add-after-delete', `Unexpected count after re-add: ${finalCount}`);

  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(400);

  // Step 4 — lift
  await page.selectOption('#lift-verdict', 'neutral');
  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(300);

  // Step 5
  await page.fill('#sum-best', 'Held together after tough session yesterday');
  await page.fill('#sum-break', 'Rep 2 slightly flat');

  page.once('dialog', d => d.accept());
  await page.click('.wizard-nav .btn-primary');
  await page.waitForTimeout(1500);

  // Verify data
  const state = await getStorageState(page);
  const sessions = state?.sessions || [];
  const s3 = sessions[sessions.length - 1];

  if (s3?.sprint?.reps?.length === 3) ok('data-integrity', 'Session 3 has 3 reps saved correctly');
  else err('data-integrity', `Session 3 reps: ${s3?.sprint?.reps?.length} (expected 3)`);

  // Check rep renumber didn't corrupt rep scores — each rep should have valid scores
  const reps3 = s3?.sprint?.reps || [];
  const allValid = reps3.every(r => r.quality >= 1 && r.quality <= 10);
  if (allValid) ok('data-integrity', 'All rep scores in session 3 are valid (1-10)');
  else err('data-integrity', 'Rep scores out of range in session 3', JSON.stringify(reps3));

  const v3 = s3?.analysis?.sessionVerdict;
  if (v3 === 'acceptable') ok('analysis-logic', 'Session 3 verdict = acceptable');
  else warn('analysis-logic', `Session 3 verdict = ${v3} (expected acceptable for Q≈7 E≈6-7)`);

  return s3;
}

// ── Cross-tab checks ──────────────────────────────────────────────────────────
async function runTabChecks(page) {
  console.log('\n═══ CROSS-TAB CHECKS ═══');

  // Plan tab
  await clickNav(page, 'plan');
  await page.waitForTimeout(500);

  const planDisplay = await page.$('#plan-display .card');
  if (planDisplay) ok('plan-tab', 'Plan tab renders a card');
  else err('plan-tab', 'Plan tab empty after 3 sessions');

  // Check plan is based on session 3 (most recent)
  const planText = await page.$eval('#plan-display', el => el.innerText).catch(() => '');
  if (planText.includes('Day') || planText.includes('fly')) {
    ok('plan-tab', 'Plan contains fly/day info');
  } else {
    warn('plan-tab', 'Plan content may be missing', planText.slice(0, 100));
  }

  // Check that plan nextPlan is populated in state
  const state = await getStorageState(page);
  const plan = state?.nextPlan;
  if (plan) ok('plan-storage', 'nextPlan stored in localStorage');
  else err('plan-storage', 'nextPlan missing from localStorage after 3 sessions');

  if (plan?.progressionDecision) ok('plan-logic', `progressionDecision = ${plan.progressionDecision}`);
  else err('plan-logic', 'progressionDecision missing from plan');

  // Verify floor/ceiling constraints
  if (plan) {
    if (plan.ceilingReps <= 6 && plan.ceilingReps >= 1) ok('plan-constraints', `ceilingReps=${plan.ceilingReps} within 1-6`);
    else warn('plan-constraints', `ceilingReps=${plan.ceilingReps} outside expected range`);
    if (plan.fly >= 10 && plan.fly <= 25) ok('plan-constraints', `fly=${plan.fly}m within 10-25`);
    else err('plan-constraints', `fly=${plan.fly}m outside 10-25`);
  }

  // Accessories in plan
  if (plan?.accessories?.length >= 2) ok('accessory-plan', `Plan has ${plan.accessories.length} accessories selected`);
  else warn('accessory-plan', `Plan has ${plan?.accessories?.length} accessories (expected ≥2)`);

  // No duplicate categories in accessories
  if (plan?.accessories) {
    const cats = plan.accessories.map(a => a.category);
    const uniqueCats = new Set(cats);
    if (cats.length === uniqueCats.size) ok('accessory-dedup', 'No duplicate categories in accessories');
    else err('accessory-dedup', 'Duplicate accessory categories in plan', cats.join(', '));
  }

  // History tab
  await clickNav(page, 'history');
  await page.waitForTimeout(500);

  const sessionCards = await page.$$('#session-cards .card, #session-cards [class*="card"]');
  if (sessionCards.length > 0) ok('history-tab', `History shows ${sessionCards.length} session cards`);
  else warn('history-tab', 'No session cards in history');

  // Chart renders
  const canvas = await page.$('#trend-chart');
  if (canvas) ok('history-chart', 'Trend chart canvas exists');
  else err('history-chart', 'Trend chart canvas missing');

  // Analyzer tab — select different sessions
  await clickNav(page, 'analyzer');
  await page.waitForTimeout(400);

  const options = await page.$$('#analyzer-session-select option');
  if (options.length >= 3) ok('analyzer-tab', `Analyzer has ${options.length} sessions to select`);
  else warn('analyzer-tab', `Only ${options.length} sessions in analyzer select`);

  // Rules tab
  await clickNav(page, 'rules');
  await page.waitForTimeout(300);

  const rulesContent = await page.$('#rules-content');
  const rulesHtml = await rulesContent?.innerHTML().catch(() => '');
  if (rulesHtml && rulesHtml.length > 100) ok('rules-tab', 'Rules content rendered');
  else err('rules-tab', 'Rules content empty or not rendered');

  // Data tab — export button present
  await clickNav(page, 'data');
  await page.waitForTimeout(200);
  const exportBtn = await page.$('button:has-text("Export JSON")');
  if (exportBtn) ok('data-tab', 'Export JSON button present');
  else err('data-tab', 'Export JSON button missing');
}

// ── Analytical logic spot-checks ──────────────────────────────────────────────
async function runLogicChecks(page) {
  console.log('\n═══ LOGIC SPOT-CHECKS ═══');

  const state = await getStorageState(page);
  const sessions = state?.sessions || [];

  // Readiness score calculation
  // s3: leg=6, gen=6, energy=7, no bad sleep → avg(6,6,7) = 6.33
  const s3 = sessions[sessions.length - 1];
  if (s3?.analysis?.readinessScore) {
    const expected = (6 + 6 + 7) / 3; // = 6.33
    const got = s3.analysis.readinessScore;
    if (Math.abs(got - expected) < 0.5) ok('readiness-calc', `readinessScore=${got} ≈ ${expected.toFixed(1)}`);
    else warn('readiness-calc', `readinessScore=${got} vs expected≈${expected.toFixed(1)}`);
  }

  // Session 2 (stop triggered) — plan should regress reps to floor
  const s2 = sessions[sessions.length - 2];
  if (s2?.analysis?.progressionDecision?.startsWith('regress')) {
    ok('regression-after-stop', 'Session 2 (stop) correctly produces regress decision');
  } else {
    err('regression-after-stop', `Session 2 (stop) decision = ${s2?.analysis?.progressionDecision}`);
  }

  // BlockManager — accessory block should be open after 3 sessions
  const blocks = state?.settings?.accessoryBlocks || [];
  if (blocks.length >= 1) ok('block-manager', `${blocks.length} accessory block(s) exist`);
  else warn('block-manager', 'No accessory blocks found — attachSession may have failed');

  const openBlock = blocks.find(b => b.status === 'open');
  if (openBlock) ok('block-manager', `Open block has ${openBlock.sessionIds.length} sessions`);
  else warn('block-manager', 'No open block — may have been closed or never opened');

  // accessoryScores initialized
  const scores = state?.settings?.accessoryScores || {};
  const scoreKeys = Object.keys(scores);
  if (scoreKeys.length > 0) ok('block-manager', `accessoryScores initialized for ${scoreKeys.length} exercises`);
  else err('block-manager', 'accessoryScores not initialized');

  // nextPlan.dayType should alternate from last session dayType
  const plan = state?.nextPlan;
  const lastDayType = sessions[sessions.length - 1]?.dayType;
  const expectedNext = lastDayType === 'day1' ? 'day2' : 'day1';
  if (plan?.dayType === expectedNext) {
    ok('plan-day-alternation', `Plan correctly alternates to ${plan.dayType} after ${lastDayType}`);
  } else {
    warn('plan-day-alternation', `Plan dayType=${plan?.dayType}, expected ${expectedNext} after ${lastDayType}`);
  }
}

// ── Main ──────────────────────────────────────────────────────────────────────
async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 480, height: 900 }
  });
  const page = await context.newPage();

  // Capture console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      err('console', msg.text().slice(0, 120));
    }
  });
  page.on('pageerror', e => {
    err('page-error', e.message.slice(0, 120));
  });

  try {
    await page.goto(URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(800);

    // Start fresh
    await clearStorage(page);

    await runSession1(page);
    await runSession2(page);
    await runSession3(page);
    await runTabChecks(page);
    await runLogicChecks(page);

  } catch (e) {
    err('test-runner', 'Unexpected error in test', e.message);
  } finally {
    await browser.close();
  }

  // ── Report ──
  console.log('\n' + '═'.repeat(60));
  console.log('FINDINGS REPORT');
  console.log('═'.repeat(60));

  const errors = FINDINGS.filter(f => f.severity === 'ERROR');
  const warnings = FINDINGS.filter(f => f.severity === 'WARN');
  const oks = FINDINGS.filter(f => f.severity === 'OK');

  console.log(`\n✓ PASSED: ${oks.length}`);
  console.log(`⚠ WARNINGS: ${warnings.length}`);
  console.log(`✗ ERRORS: ${errors.length}`);

  if (errors.length > 0) {
    console.log('\n--- ERRORS ---');
    errors.forEach(f => console.log(`  [${f.category}] ${f.msg}${f.detail ? ' — ' + f.detail : ''}`));
  }

  if (warnings.length > 0) {
    console.log('\n--- WARNINGS ---');
    warnings.forEach(f => console.log(`  [${f.category}] ${f.msg}${f.detail ? ' — ' + f.detail : ''}`));
  }

  return { errors, warnings, oks };
}

main().catch(console.error);
