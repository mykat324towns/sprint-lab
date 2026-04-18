# SPRINT LAB SYSTEM AUDIT — v1.0
**Date:** 2026-04-17 | **App:** Sprint Lab (Index.html + server.js) | **Protocol:** 35–40m buildup → 12–15m fly

---

## SECTION 1 — Extracted Logic (Clean Bullets)

### Session Verdict Classification
- **Strong:** qualAvg ≥ 7.5 AND easeAvg ≥ 7.0 AND sessionConsistency ≥ 0.7 AND no stop
- **Acceptable:** qualAvg ≥ 6.0 AND easeAvg ≥ 6.0 AND no stop
- **Degraded:** any other condition (thresholds not met OR stop triggered)
- **Abort:** stop triggered within first 2 reps

### Fatigue Detection
- **Fatigue Pattern (UPDATED):** (slope < −0.4 AND qualDrop ≥ 2 AND easeDrop ≥ 1.5 AND reps ≥ 4) OR (qualDrop ≥ 3) OR (slope < −0.6 AND qualDrop ≥ 1.5 AND reps ≥ 4)
- **Quality Drop:** qualDropFromBest ≥ 2 OR verdict = degraded
- **Rhythm Loss:** rhythmAvg < 6 AND (qualAvg − rhythmAvg) > 1.5
- **Low Readiness:** avg(legFresh, genFresh, energy) < 5

### Issue Type Classification (ordered priority)
1. Lift Interference: fatiguePattern AND Day2 AND liftDose=risk
2. Fatigue: fatiguePattern
3. Force/Stiffness: easeArr[0] ≤ 6 AND qualAvg ≤ 6.5 (from rep 1)
4. Coordination: rhythmAvg < 6 AND qual−rhythm gap > 1.5
5. Exposure: 3 consecutive acceptable+ sessions with identical fly and reps, consistency ≥ 0.7

### Progression Rules (UPDATED)
- **Regress fly (−5m, reset reps):** 2nd consecutive degraded AND issueType=force
- **Regress reps (drop to floor):** degraded/abort/stop (non-force path)
- **Progress fly (+5m, reset reps):** 2 consecutive strong+consistent, completed ceiling reps (≥4), fly unchanged 2+ sessions, readiness ≥ readinessGate
- **Progress reps (+1, cap 5):** 2 consecutive strong+consistent, completed ceiling, readiness ≥ readinessGate
- **readinessGate:** 5 if aiContextOnly or recentNoteOnly (off-season), else 6
- **Hold:** default

### Sprint Dose
- Low: stop triggered AND reps < floorReps
- High: reps > ceilingReps
- Good: everything else

### Lift Volume
- Decrease sets (−1, floor 2): fatiguePattern OR liftDose=risk OR lift_interference OR progression=regress
- Increase sets (+1, ceiling 5): sprintUp OR strong+consistent
- Hold: default

### Accessory Selection
- Issue type maps to target qualities → filters exercise pool
- Sorts by CNS load (ascending) when fatigued
- Selects 2–3 exercises avoiding duplicate categories
- Block closes after 6 sessions or accessory change
- Rotate out after 2 consecutive negative block outcomes

---

## SECTION 2 — Structured Rules (IF/THEN)

```
FATIGUE (UPDATED — OR logic, slope gated to ≥4 reps)
IF (reps ≥ 4 AND slope < -0.4 AND qualDrop ≥ 2 AND easeDrop ≥ 1.5)
  OR (qualDrop ≥ 3)
  OR (reps ≥ 4 AND slope < -0.6 AND qualDrop ≥ 1.5)
  → fatiguePattern = TRUE

IF fatiguePattern = TRUE
  → issueType = 'fatigue'
  → suppress_progression = TRUE

IF readiness_avg < 5
  → lowReadiness = TRUE
  → suppress_progression = TRUE

READINESS GATE (UPDATED — off-season aware)
IF currentSession.aiContextOnly OR any prior 2 sessions were note_only
  → readinessGate = 5
ELSE
  → readinessGate = 6

PROGRESSION — FLY
IF sessionVerdict = 'strong' (current + prior) AND consistency >= 0.7 (both)
   AND reps >= ceilingReps AND ceilingReps >= 4
   AND fly unchanged last 2+ sessions AND readiness >= readinessGate
  → progressionDecision = 'progress_fly' (+5m, reset to floorReps)

PROGRESSION — REPS (UPDATED — capped at 5)
IF sessionVerdict = 'strong' (current + prior) AND consistency >= 0.7 (both)
   AND reps >= ceilingReps AND readiness >= readinessGate
  → progressionDecision = 'progress_reps' (+1 rep, hard ceiling 5)

REGRESSION — REPS
IF effectiveStop OR verdict = 'degraded' OR verdict = 'abort'
  → progressionDecision = 'regress_reps' (drop to floor)

REGRESSION — FLY
IF prior session also degraded AND issueType = 'force'
  → progressionDecision = 'regress_fly' (-5m)

ISSUE — FORCE
IF easeArr[0] <= 6 AND qualAvg <= 6.5
  → issueType = 'force' (poor from rep 1 = force limiter, not accumulated fatigue)

ISSUE — COORDINATION
IF rhythmAvg < 6 AND (qualAvg - rhythmAvg) > 1.5
  → issueType = 'coordination'

LIFT VOLUME
IF fatiguePattern = TRUE OR liftDose = 'risk' OR progressionDecision.startsWith('regress')
  → lift sets -= 1 (floor: 2)

IF progressionDecision = 'progress_reps' OR 'progress_fly' OR (strong + consistent)
  → lift sets += 1 (ceiling: 5)

OFF-SEASON / RETURN
IF session notes contain 'first day back' OR 'off-season' OR 'return from break'
  → bias = 'note_only' (data not comparable to pre-break baseline)
  → flags: flat_cns + low_pop
  → readinessGate drops to 5 for next 2 sessions
```

---

## SECTION 3 — Research Findings (With Sources)

### R1: CNS Fatigue Markers in Sprint Athletes
- Ground contact time increases 5–15% before velocity measurably drops
- CMJ height is a reliable proxy for neuromuscular readiness between sessions
- First-step quickness is highly CNS-sensitive
- Recovery from neural-intensive sprint sessions: 48–72+ hours
- **Sources:** PMC11143976 (CMJ as sprint fatigue tool, 2024); The Speed Project neuromuscular fatigue article

### R2: Within-Session Fatigue Detection
- Velocity loss % is the most validated intra-session fatigue metric (not subjective quality)
- Technical breakdown in mechanics appears *before* measurable speed loss
- Optimal max velocity session volume: 300–400m total to prevent excessive neural load
- Jump height loss correlates with sprint fatigue
- **Sources:** PMC4213373 (monitoring training load, 2014); Jimenez-Reyes et al., 2018 (JSS)

### R3: Fly Sprint Protocol — Distance Validity
- Flying sprint zones of 20–30m are the standard research and field protocol
- 10–20m zones are used for *measurement* of max velocity, not development
- Acceleration zone: 20–25m for developing athletes, 30–50m for advanced/elite
- A 35–40m build is well within the supported range for reaching max velocity
- 12–15m fly captures top-end speed in the deceleration onset window — valid for quality assessment and short max velocity exposure; shorter than typical volume-development protocols
- **Sources:** TopEndSports fly sprint protocol; Freelap USA (max velocity measurement); SpeedEndurance.com (flying 30 protocol)

### R4: Max Velocity Volume Progression
- Elite protocols: ~2000m total volume in general prep, ~1000m in competition phase
- Quality reps kept to 3–5 per session for max velocity work
- 5×50m across 2 days > 10×50m in 1 session for adaptation
- **Sources:** SimpliFaster "Dosage Debate" article; Haugen et al. 2019 (Springer)

### R5: Two-Session Quality Gates
- Autoregulation in training is research-supported (HRV, wellness scores, RSI)
- No sprint-specific evidence for 2-consecutive-session gates before progression
- **Sources:** PMC7706636 (methods for regulating resistance training, 2020); PMC7575491 (autoregulation inconsistencies, 2020)

### R6: Concurrent Training Interference
- Strength before sprints same-day: impairs sprint output
- 6+ hour separation: interference largely eliminated
- Next-day carryover fatigue is real after heavy lower body work
- **Sources:** Springer (Optimizing Resistance Training, 2024)

### R7: Quality-First Max Velocity
- Keep quality high — never sprint through fatigue for max velocity development
- 5% velocity decline: widely cited stop point for max velocity sets
- **Sources:** NSCA (Designing Speed Training Sessions); SimpliFaster dosage article

### R8: Detraining & Return From Break
- < 4 weeks: minimal impact on sprint speed
- > 4 weeks: significant max velocity decline begins
- High-force outputs (strength) degrade faster than high-velocity outputs
- **Sources:** PLOS ONE (detraining repeated sprint, 2018); Whistle Performance detraining article

---

## SECTION 4 — Validation Table

| Rule | Assumption | Evidence | Status |
|---|---|---|---|
| Slope < −0.4 triggers fatigue (gated to ≥4 reps) | Negative quality trend = CNS fatigue | Trend detection valid; threshold arbitrary but now rep-count stable | **PARTIALLY SUPPORTED** |
| qualDropFromBest ≥ 3 alone triggers fatigue | Severe drop from peak = fatigue regardless of slope | Drop-from-best velocity validated; severe drop path is conservative catch | **PARTIALLY SUPPORTED** |
| easeDrop ≥ 1.5 as supporting signal | Perceived effort tracks fatigue | RPE tracks fatigue; combined with slope/drop = reasonable | **PARTIALLY SUPPORTED** |
| rhythmAvg < 6 AND qual−rhythm > 1.5 = coordination | Rhythm dissociation distinct from fatigue | Neurologically sound | **VALIDATED** |
| easeArr[0] ≤ 6 = force issue (not fatigue) | Poor from rep 1 = force expression limit | Distinguishing fatigue from force capacity is valid; rep 1 ease as gate is logical | **VALIDATED** |
| 2 consecutive strong sessions → progress fly | Sustained quality = readiness for load increase | Autoregulation principle supported; specific 2-session rule lacks direct evidence | **PARTIALLY SUPPORTED** |
| +5m fly increment | Smallest meaningful change in max velocity stimulus | No specific research; conservative load management | **WEAK / NO SUPPORT** |
| +1 rep increment, capped at 5 | Smallest volume change; 5 reps = max CNS-safe ceiling | 3–5 high-quality reps is coaching consensus for max velocity | **VALIDATED** (cap) |
| 35–40m build → 12–15m fly | Build sufficient to reach max velocity; fly = max velocity zone | 35–40m is within supported acceleration range; 12–15m fly captures onset of deceleration | **PARTIALLY SUPPORTED** |
| Lift sets ↓ when fatiguePattern | Residual fatigue from lifting impairs sprint quality | Concurrent training interference is well-supported | **VALIDATED** |
| readinessGate drops to 5 in off-season context | Off-season baselines are systemically lower | Detraining research supports lower readiness post-break | **VALIDATED** |
| note_only for first session back | Performance post-break not comparable to pre-break baseline | Strongly supported by detraining research | **VALIDATED** |
| flat_cns + low_pop flags on return | Off-season = CNS/force output reduced | Power declines faster than speed; CMJ drops after 2 weeks | **VALIDATED** |
| Accessory selection by issueType | Sprint issues map to specific mechanical deficits | Logical framework; direct accessory-to-sprint-outcome evidence thin | **PARTIALLY SUPPORTED** |
| Block closes at 6 sessions | 6 sessions = sufficient adaptation window | Reasonable but arbitrary | **WEAK / NO SUPPORT** |
| 2 consecutive negative blocks → rotate out | Non-responsive exercises should be replaced | Logical; no sprint-specific evidence for this threshold | **PARTIALLY SUPPORTED** |

---

## SECTION 5 — Risks / Issues

### RISK 1 — Triple-AND Fatigue Gate Was Too Conservative *(FIXED)*
**Problem:** `slope < -0.4 AND qualDrop >= 2 AND easeDrop >= 1.5` — all three required. Real fatigue events with two-of-three conditions were classified as non-fatigue.
**Fix applied:** OR paths added for single-signal severe drops; slope gated to minimum 4 reps.

### RISK 2 — Slope Threshold Was Rep-Count Dependent *(FIXED)*
**Problem:** `trendScore = raw linear slope` — magnitude differs between 3-rep and 6-rep sessions for the same trajectory.
**Fix applied:** Slope-based fatigue now requires `qualArr.length >= 4` before activating.

### RISK 3 — Subjective Quality ≠ Velocity *(Structural Limitation — No Code Fix)*
**Problem:** All fatigue logic built on 1–10 subjective ratings. Research validates velocity loss % as gold standard. Subjective quality adds noise; CNS fatigue impairs proprioception and self-assessment.
**Implication:** System is best understood as a subjective-perception tracker with research-aligned heuristics, not a velocity-measurement system. Acceptable given no hardware, but interpretation should account for this.

### RISK 4 — Max Rep Ceiling Was 6 *(FIXED)*
**Problem:** 6 reps at true max velocity creates excessive CNS load. Coaching consensus: 3–5 high-quality reps is the validated max velocity development range.
**Fix applied:** `Math.min(5, ...)` hard cap on rep progression.

### RISK 5 — Progression Gate Too Strict for Early Off-Season *(FIXED)*
**Problem:** readiness ≥ 6 gate combined with "strong" verdict thresholds designed for competition phase, not early off-season where baselines are systemically lower.
**Fix applied:** `readinessGate = 5` when current or recent prior sessions were note_only (off-season context).

### RISK 6 — 12–15m Fly Zone (Protocol Note — Not a Bug)
**Context:** 35–40m build reaching max velocity; 12–15m fly = onset of deceleration zone. Not the standard development protocol (20–30m fly is more common). Acceptable as a quality/exposure tool in early off-season where high volumes are not the goal. Watch for stiffness and contact time — they're harder to perceive in a 12–15m window.

### RISK 7 — Accessory CNS Sort Doesn't Track Readiness Score Directly
**Problem:** Low-CNS-first sort activates on `fatiguePattern` flag only. Low readiness without fatiguePattern still allows high-CNS accessory selection.
**Status:** Minor mismatch. No fix applied — would require readiness score to pass into accessory selector.

---

## SECTION 6 — Improved Rules (Applied)

### FIX 1 — Protocol (User-Confirmed)
**Protocol:** Build: 35–40m → Fly: 12–15m
**Default updated:** Build default changed from 30m → 35m in input fields and data structures.

### FIX 2 + FIX 3 — Fatigue Gate + Slope Guard
```javascript
// Before
const fatiguePattern = trendScore < -0.4 && qualDropFromBest >= 2 && easeDropFromBest >= 1.5;

// After
const slopeValid = qualArr.length >= 4;
const fatiguePattern =
  (slopeValid && trendScore < -0.4 && qualDropFromBest >= 2 && easeDropFromBest >= 1.5) ||
  (qualDropFromBest >= 3) ||
  (slopeValid && trendScore < -0.6 && qualDropFromBest >= 1.5);
```

### FIX 4 — Max Rep Ceiling
```javascript
// Before
suggestedReps = Math.min(6, sprint.ceilingReps + 1);

// After
suggestedReps = Math.min(5, sprint.ceilingReps + 1);
```

### FIX 5 — Off-Season Readiness Gate
```javascript
// Added before progressionDecision logic
const recentNoteOnly = priorSessions && priorSessions.slice(-2).some(s =>
  (s.aiOutputs || {}).pre_session && s.aiOutputs.pre_session.planner_impact_bias === 'note_only');
const readinessGate = (aiContextOnly || recentNoteOnly) ? 5 : 6;

// Progression gates use readinessGate instead of hardcoded 6
```

### FIX 6 — Slope Threshold Calibration (Ongoing Recommendation)
No code change. When 10+ sessions are logged: compare `trendScore` distribution between sessions you rate as "fatigued" vs "fine" in notes. Recalibrate the −0.4 threshold against your actual data. The current value is theoretically reasonable but empirically unverified for this athlete.

---

*Sources: PMC11143976, PMC4213373, PMC7134353, PMC7706636, PMC7575491, PLOS ONE 2018 (detraining), Haugen et al. 2019 (Springer), Jimenez-Reyes et al. 2018 (JSS), SimpliFaster dosage article, NSCA speed training article, Freelap USA max velocity article.*
