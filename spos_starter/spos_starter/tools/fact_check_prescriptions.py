"""
Fact-check the current session's exercise prescriptions against Perplexity (sonar-pro).

Steps:
  1. Playwright opens the app, screenshots the Plan tab, extracts localStorage state
  2. Parses the next plan's exercises + accessories from state
  3. Sends prescriptions as structured text to Perplexity sonar-pro for sports-science review
  4. Writes a flagged markdown report → tmp/fact_check_YYYY-MM-DD_HHMM.md

Usage:
  python tools/fact_check_prescriptions.py
  python tools/fact_check_prescriptions.py --url http://localhost:3000
  python tools/fact_check_prescriptions.py --url "file:///C:/Users/jaxdo/Downloads/Sprint Research and Program/Index.html"
  python tools/fact_check_prescriptions.py --no-screenshot   # skip browser, use existing state from --state-file
"""

import json
import os
import sys
import argparse
import requests
from datetime import datetime
from pathlib import Path

# Load .env
ROOT = Path(__file__).parent.parent
env_path = ROOT / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, _, v = line.partition('=')
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))


# ──────────────────────────────────────────────
# 1. SCREENSHOT + EXTRACT
# ──────────────────────────────────────────────

def screenshot_and_extract(url: str):
    """Open app in Playwright, screenshot Plan tab, extract localStorage."""
    from playwright.sync_api import sync_playwright

    headless = os.environ.get('PLAYWRIGHT_HEADLESS', 'true').lower() == 'true'
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    screenshot_path = ROOT / 'tmp' / f'fact_check_{ts}.png'

    print(f'  Opening: {url}')
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        page.goto(url, wait_until='domcontentloaded', timeout=15000)
        page.wait_for_timeout(1500)

        # Click Plan tab
        try:
            page.locator('text=Plan').first.click(timeout=3000)
            page.wait_for_timeout(1000)
        except Exception:
            print('  [warn] Could not click Plan tab — screenshotting current view.')

        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f'  Screenshot saved → tmp/{screenshot_path.name}')

        # Pull localStorage
        state_json = page.evaluate("() => localStorage.getItem('sprintlab_v1')")
        browser.close()

    return screenshot_path, state_json


# ──────────────────────────────────────────────
# 2. PARSE PRESCRIPTIONS
# ──────────────────────────────────────────────

def extract_prescriptions(state_json: str):
    """Return dict of prescriptions from stored app state."""
    if not state_json:
        return None
    try:
        state = json.loads(state_json)
    except json.JSONDecodeError:
        print('  [warn] Could not parse localStorage JSON.')
        return None

    plan = state.get('nextPlan')
    if not plan:
        print('  [warn] No nextPlan found in state. Log a session first.')
        return None

    return {
        'exercises':          plan.get('exercises', []),
        'accessories':        plan.get('accessories', []),
        'liftDecision':       plan.get('liftDecision', 'hold'),
        'liftVolumeNote':     plan.get('liftVolumeNote', ''),
        'progressionDecision': plan.get('progressionDecision', 'hold'),
        'basedOnSessionDate': plan.get('basedOnSessionDate', 'unknown'),
        'reasons':            plan.get('reasons', {}),
    }


# ──────────────────────────────────────────────
# 3. BUILD PERPLEXITY PROMPT
# ──────────────────────────────────────────────

ATHLETE_CONTEXT = (
    "Athlete: sprinter, strong acceleration, weak max velocity. "
    "Goal: improve max velocity via force expression, ankle/foot stiffness, "
    "touchdown coordination, upright posture exposure. No active injuries. "
    "Program philosophy: sprint quality first, no grinding lifts, low-fatigue high-transfer decisions."
)

def build_prompt(rx: dict) -> str:
    lines = [
        "You are a sports science expert reviewing exercise prescriptions for a sprint athlete.",
        "",
        f"Context: {ATHLETE_CONTEXT}",
        "",
        "## Prescriptions to Review",
        "",
    ]

    if rx.get('exercises'):
        lines.append("### Main Lifts")
        for ex in rx['exercises']:
            s = ex.get('sets', '?')
            r = ex.get('reps', '?')
            rpe = ex.get('rpe', '')
            load = ex.get('load', '')
            line = f"- {ex.get('name', '?')}: {s} sets × {r} reps"
            if rpe: line += f" @ RPE {rpe}"
            if load: line += f" | {load}"
            lines.append(line)
        lines.append("")

    if rx.get('accessories'):
        lines.append("### Accessories")
        for acc in rx['accessories']:
            name = acc.get('name') or acc.get('id', '?')
            cat  = acc.get('category', '')
            lines.append(f"- {name}" + (f" ({cat})" if cat else ""))
        lines.append("")

    if rx.get('liftVolumeNote'):
        lines.append(f"Volume guidance: {rx['liftVolumeNote']}")
        lines.append("")

    lines += [
        "## Fact-Check Instructions",
        "",
        "For EACH prescription above:",
        "- ✓ if evidence-based and appropriate for this athlete's goal",
        "- ⚠ if questionable — explain why and what to watch",
        "- ✗ if contraindicated or misaligned with max velocity development",
        "",
        "Also note: are there any commonly recommended exercises for max-velocity development that are MISSING from this program?",
        "",
        "Be concise. One bullet per item. Cite the mechanism (not just 'research shows').",
    ]

    return "\n".join(lines)


# ──────────────────────────────────────────────
# 4. CALL PERPLEXITY
# ──────────────────────────────────────────────

def call_perplexity(prompt: str) -> str:
    api_key = os.environ.get('OPENAI_API_KEY', '').strip()
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY (OpenRouter key) is not set in .env."
        )

    resp = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
            'HTTP-Referer': 'https://sprintlab.local',
        },
        json={
            'model': 'perplexity/sonar-pro',
            'messages': [
                {
                    'role': 'system',
                    'content': (
                        'You are a concise sports science expert specializing in sprint performance. '
                        'Respond with evidence-based bullet points only. No preamble.'
                    ),
                },
                {'role': 'user', 'content': prompt},
            ],
            'max_tokens': 1800,
        },
        timeout=30,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"OpenRouter API error {resp.status_code}: {resp.text}")

    data = resp.json()
    return data['choices'][0]['message']['content']


# ──────────────────────────────────────────────
# 5. WRITE REPORT
# ──────────────────────────────────────────────

def write_report(rx, analysis: str, screenshot_path) -> Path:
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    slug = datetime.now().strftime('%Y-%m-%d_%H%M')
    report_path = ROOT / 'tmp' / f'fact_check_{slug}.md'

    lines = [
        f"# Prescription Fact-Check — {ts}",
        "",
    ]

    if screenshot_path:
        lines += [f"Screenshot: `tmp/{Path(screenshot_path).name}`", ""]

    if rx:
        session_date = rx.get('basedOnSessionDate', 'unknown')
        lines += [f"Based on session: {session_date}", ""]

        lines.append("## Prescriptions Reviewed")
        lines.append("")
        if rx.get('exercises'):
            lines.append("**Main Lifts:**")
            for ex in rx['exercises']:
                s, r = ex.get('sets', '?'), ex.get('reps', '?')
                rpe = ex.get('rpe', '')
                lines.append(f"- {ex.get('name')}: {s}×{r}" + (f" @ RPE {rpe}" if rpe else ""))
        if rx.get('accessories'):
            lines.append("")
            lines.append("**Accessories:**")
            for acc in rx['accessories']:
                lines.append(f"- {acc.get('name') or acc.get('id')}")
        if rx.get('liftVolumeNote'):
            lines += ["", f"*Volume note: {rx['liftVolumeNote']}*"]
        lines.append("")

    lines += [
        "## Perplexity Analysis (sonar-pro)",
        "",
        analysis,
        "",
        "---",
        "*Action: review flags above. Update the exercise library or biomechanics_principles.json manually if needed.*",
    ]

    report_path.write_text("\n".join(lines), encoding='utf-8')
    return report_path


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Fact-check exercise prescriptions via Perplexity.')
    parser.add_argument('--url', default='http://localhost:3000',
                        help='App URL (default: http://localhost:3000). Use file:// for local HTML.')
    parser.add_argument('--no-screenshot', action='store_true',
                        help='Skip browser step; use --state-file instead.')
    parser.add_argument('--state-file', default=None,
                        help='Path to a JSON file containing the sprintlab_v1 localStorage value.')
    args = parser.parse_args()

    print('\n' + '='*60)
    print('FACT CHECK — EXERCISE PRESCRIPTIONS')
    print('='*60)

    screenshot_path = None
    state_json = None

    if args.no_screenshot:
        if not args.state_file:
            print('[error] --no-screenshot requires --state-file.')
            sys.exit(1)
        state_json = Path(args.state_file).read_text(encoding='utf-8')
        print(f'  Loaded state from: {args.state_file}')
    else:
        print('\nStep 1 — Screenshot + extract state')
        screenshot_path, state_json = screenshot_and_extract(args.url)

    print('\nStep 2 — Parse prescriptions')
    rx = extract_prescriptions(state_json)
    if not rx:
        print('  No prescriptions to check. Exiting.')
        sys.exit(0)
    print(f"  Found {len(rx.get('exercises', []))} main lifts, {len(rx.get('accessories', []))} accessories.")

    print('\nStep 3 — Call Perplexity sonar-pro')
    prompt = build_prompt(rx)
    analysis = call_perplexity(prompt)
    print('  Done.')

    print('\nStep 4 — Write report')
    report_path = write_report(rx, analysis, screenshot_path)
    print(f'  Report → {report_path.relative_to(ROOT)}')

    print('\n' + '='*60)
    print('DONE — open the report to review flags.')
    print('='*60 + '\n')


if __name__ == '__main__':
    main()
