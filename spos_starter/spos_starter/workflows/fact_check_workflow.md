# Fact-Check Workflow

## Objective
Screenshot the current plan, extract exercise prescriptions, send to Perplexity sonar-pro for sports-science validation, and flag anything misaligned with max-velocity development.

## Prerequisites
1. Add your Perplexity API key to `.env`:
   ```
   PERPLEXITY_API_KEY=pplx-...
   ```
   Get one at: perplexity.ai/settings/api

2. Playwright browsers installed:
   ```
   playwright install chromium
   ```

3. A session logged in the app (Plan tab must have a generated plan).

## Steps

### Option A — App running via server
```bash
# Terminal 1
node server.js

# Terminal 2
cd spos_starter
python tools/fact_check_prescriptions.py --url http://localhost:3000
```

### Option B — App opened as a local file
```bash
cd spos_starter
python tools/fact_check_prescriptions.py \
  --url "file:///C:/Users/jaxdo/Downloads/Sprint Research and Program/Index.html"
```

### Option C — Skip browser (already have state JSON)
```bash
python tools/fact_check_prescriptions.py \
  --no-screenshot \
  --state-file path/to/state.json
```

## Output
- Screenshot → `tmp/fact_check_YYYYMMDD_HHMMSS.png`
- Report     → `tmp/fact_check_YYYY-MM-DD_HHMM.md`

## Reading the Report
Each prescription is marked:
- ✓ Evidence-based, appropriate for the athlete
- ⚠ Questionable — review the note, consider adjusting
- ✗ Contraindicated or misaligned with max-velocity goal

## After Review
Human decides what changes to make:
- Update sets/reps/RPE in the Manual Override card (Plan tab)
- Swap accessories in the Log page accessory pickers
- Edit `biomechanics_principles.json` if a principle is wrong

## What Perplexity Checks Against
- Sports science literature on max-velocity mechanics
- Force-velocity profile alignment
- Fatigue cost vs. transfer value
- Commonly missing exercises for upright sprint posture
