"""
Write Phase 0 sprint program to Notion.
Creates two rows in the Sprint Program database: Day 1 and Day 2.
Schema: Day | Focus | Sprint Plan | Lift Plan | Notes
"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))
from notion_write import write_program
from dotenv import load_dotenv

load_dotenv(os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env")))

# ──────────────────────────────────────────────
# SPRINT STRUCTURE (same protocol both days)
# ──────────────────────────────────────────────

SPRINT_PROTOCOL = (
    "STRUCTURE: Pure singles. Full CNS recovery between every rep.\n\n"
    "PRIMER REPS (not counted in volume):\n"
    "  2 x (25-30m build -> 10m fly) at relaxed effort\n"
    "  Rest 5 min after primers before starting main work\n"
    "  Purpose: prime CNS, establish pattern. Do NOT chase speed.\n\n"
    "MAIN REPS:\n"
    "  Format: 1 rep -> full rest (6-8 min, walk back + standing) -> repeat\n"
    "  Build: 25-30m (bias toward longer — athlete enters fly already upright at max velocity)\n"
    "  Fly zone: 15m, constant across all reps and all sessions in Phase 0\n"
    "  Floor: 3 main reps minimum\n"
    "  Ceiling: 4-6 reps ONLY if each rep is identical in quality to rep 1\n\n"
    "STOP IMMEDIATELY when:\n"
    "  - Rep feels forced or muscular (not reflexive)\n"
    "  - Contact time visibly increases on video (GCT lengthening)\n"
    "  - Posture breaks: anterior tilt, forward lean, neck tension\n\n"
    "CUES:\n"
    "  'Land under you, not in front' (touchdown timing)\n"
    "  'Stay tall through the fly, eyes forward' (upright posture)\n"
    "  'Let the ground push you up — do not push the ground' (stiffness, not active push)"
)

# ──────────────────────────────────────────────
# LIFT — DAY 1
# ──────────────────────────────────────────────

DAY1_LIFT = (
    "BACK SQUAT\n"
    "  3-5 sets x 3-5 reps\n"
    "  Heavy. Stop 1-2 reps before grind. No grinding.\n\n"
    "RDL\n"
    "  3 sets x 5-6 reps\n"
    "  Full hip hinge, controlled descent.\n\n"
    "SINGLE-LEG DROP LANDING -> HOLD\n"
    "  3 sets x 4-5 reps/leg\n"
    "  Step off box ~30cm. Land stiff, hold 2s. Fast contact — not a squat.\n"
    "  Trains touchdown stiffness and coordination directly.\n\n"
    "ANKLE-STIFF POGOS (optional — Day 1 only if sprint left capacity)\n"
    "  2-3 sets x 6 reps\n"
    "  GCT target < 150ms. Reflexive, not jumpy. Skip if sprint caused fatigue."
)

# ──────────────────────────────────────────────
# LIFT — DAY 2
# ──────────────────────────────────────────────

DAY2_LIFT = (
    "BACK SQUAT\n"
    "  3-5 sets x 3-5 reps\n"
    "  Heavy. Stop 1-2 reps before grind.\n\n"
    "RDL\n"
    "  3 sets x 5-6 reps\n"
    "  Full hip hinge, controlled descent.\n\n"
    "LEG CURL or NORDIC CURL\n"
    "  3 sets x 4-5 reps\n"
    "  Controlled eccentric, aggressive concentric.\n"
    "  Supports RFD and hip extension mechanics at high velocity.\n\n"
    "COPENHAGEN HOLD (optional)\n"
    "  2 sets x 10s/side\n"
    "  Adductor stability. Keep if athlete shows medial weakness. Drop if not needed."
)

# ──────────────────────────────────────────────
# NOTES
# ──────────────────────────────────────────────

SHARED_DIAGNOSTICS = (
    "DIAGNOSTICS:\n\n"
    "Coordination issue (Mechanism #2 primary):\n"
    "  - Every rep feels like 'reaching' — extending foot forward to find ground\n"
    "  - Foot landing visibly in front of hip on video\n"
    "  - Braking sensation at contact\n"
    "  Action: reduce fly to 10m, sharpen touchdown cues\n\n"
    "Force expression issue (Mechanism #1 primary):\n"
    "  - Reps feel effortful/muscular — grinding, not bouncing\n"
    "  - Visible GCT lengthening on video (hip drops at contact)\n"
    "  - No spring quality across session\n"
    "  Action: reduce to floor reps (3), add drop landing emphasis in lift\n\n"
    "Exposure issue (insufficient stimulus):\n"
    "  - Quality holds but no progress across weeks\n"
    "  - Reps feel easy but no elasticity development\n"
    "  Action: extend fly to 20m\n\n"
    "VIDEO CHECK (every session):\n"
    "  - Did GCT shorten vs prior session?\n"
    "  - Did foot placement move under hip vs in front?\n"
    "  - Did posture hold through the full fly zone?"
)

SHARED_PROGRESSION = (
    "PROGRESSION RULES:\n\n"
    "Add reps:\n"
    "  Ceiling reps feel as clean as rep 1 across 2 consecutive sessions\n"
    "  -> Add 1 rep next session (max 6 main reps)\n\n"
    "Extend fly:\n"
    "  5+ main reps elastic at 15m fly across 2 consecutive sessions\n"
    "  -> Extend to 20m. Hold at 20m until quality confirms. Then -> 25m.\n\n"
    "Reduce:\n"
    "  Any forced rep on Day 1 -> drop to floor reps (3), hold fly distance\n"
    "  Do not reduce build distance.\n\n"
    "Phase exit (all three required):\n"
    "  1. 5+ main reps consistently elastic (reflexive feel, not muscular)\n"
    "  2. GCT visibly shorter on video (hip position higher at contact)\n"
    "  3. Quality holds across both days without fatigue drop\n"
    "Duration: 3 weeks minimum, 4 weeks typical. Exit on criteria, not clock."
)

DAY1_NOTES = (
    "PHASE 0 | Day 1 = PRIMARY exposure session\n\n"
    "Goal: maximize high-quality max velocity reps before fatigue onset.\n"
    "Full protocol. Do not cut reps unless stop criteria are met.\n\n"
    + SHARED_DIAGNOSTICS + "\n\n" + SHARED_PROGRESSION
)

DAY2_NOTES = (
    "PHASE 0 | Day 2 = CONFIRMATION session\n\n"
    "Goal: confirm Day 1 quality holds. Not additional volume.\n"
    "If Day 1 was high quality -> replicate it.\n"
    "If Day 1 was compromised -> floor reps only (3 main reps).\n\n"
    "LIFT RULES:\n"
    "  All accessories must map to sprint execution (stiffness, touchdown, hip extension).\n"
    "  No band work. No low-stimulus movements. Max 2 accessories per day. 1 preferred.\n\n"
    + SHARED_DIAGNOSTICS + "\n\n" + SHARED_PROGRESSION
)


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

DAY1_SPRINT = SPRINT_PROTOCOL + "\n\nRole: PRIMARY — full protocol."
DAY2_SPRINT = SPRINT_PROTOCOL + "\n\nRole: CONFIRMATION — same protocol. Drop to floor reps (3) if any residual fatigue from Day 1."


def main():
    print("Writing Phase 0 to Notion...\n")

    day1_id = write_program({
        "day":         "Day 1 - Sprint + Lift (Primary)",
        "focus":       "Max Velocity Exposure - Primary Session | Phase 0",
        "sprint_plan": DAY1_SPRINT,
        "lift_plan":   DAY1_LIFT,
        "notes":       DAY1_NOTES,
    })
    print(f"Day 1 page created: {day1_id}\n")

    day2_id = write_program({
        "day":         "Day 2 - Sprint + Lift (Confirmation)",
        "focus":       "Max Velocity Exposure - Confirmation Session | Phase 0",
        "sprint_plan": DAY2_SPRINT,
        "lift_plan":   DAY2_LIFT,
        "notes":       DAY2_NOTES,
    })
    print(f"Day 2 page created: {day2_id}\n")

    print("Done. Phase 0 written to Notion.")


if __name__ == "__main__":
    main()
