import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
const PORT = process.env.PORT || 3001;
const API_KEY = process.env.OPENROUTER_API_KEY || process.env.OPENAI_API_KEY;
const MODEL = process.env.OPENROUTER_MODEL || 'anthropic/claude-sonnet-4-6';
const OR_BASE = 'https://openrouter.ai/api/v1';

app.use(cors({ origin: ['http://localhost:3001', 'http://127.0.0.1:3001', 'null'] }));
app.use(express.json());
app.use(express.static(__dirname));

// ─── Schemas ────────────────────────────────────────────────────────────────

const SCHEMAS = {
  pre_session: {
    required: ['readiness_flags', 'risk_flags', 'coach_summary', 'planner_impact_bias', 'confidence'],
    enums: {
      readiness_flags: ['low_pop', 'flat_cns', 'slight_tightness', 'high_readiness', 'mentally_sharp', 'low_motivation'],
      risk_flags: ['tightness_warning', 'technical_instability', 'fatigue_pattern', 'execution_noise', 'none'],
      planner_impact_bias: ['none', 'suppress_progression', 'favor_hold', 'favor_regress', 'note_only']
    },
    arrayFields: ['readiness_flags', 'risk_flags']
  },
  rep_note: {
    required: ['rep_tags', 'risk_flags', 'coach_summary', 'planner_impact_bias', 'confidence'],
    enums: {
      rep_tags: ['felt_fast', 'rhythm_loss', 'posture_loss', 'good_projection', 'good_stiffness', 'forced_stride', 'low_bounce', 'smooth'],
      risk_flags: ['tightness_warning', 'technical_instability', 'fatigue_pattern', 'execution_noise', 'none'],
      planner_impact_bias: ['none', 'suppress_progression', 'favor_hold', 'favor_regress', 'note_only']
    },
    arrayFields: ['rep_tags', 'risk_flags']
  },
  stop_reason_normalize: {
    required: ['normalized_stop_reason', 'risk_flags', 'coach_summary', 'planner_impact_bias', 'confidence'],
    enums: {
      normalized_stop_reason: ['speed_drop', 'rhythm_loss', 'posture_breakdown', 'tightness_warning', 'low_pop', 'mental_flatness', 'planned_cap'],
      risk_flags: ['tightness_warning', 'technical_instability', 'fatigue_pattern', 'execution_noise', 'none'],
      planner_impact_bias: ['none', 'suppress_progression', 'favor_hold', 'favor_regress', 'note_only']
    },
    arrayFields: ['risk_flags']
  },
  session_summary: {
    required: ['primary_issue', 'secondary_issue', 'session_pattern', 'coach_summary', 'planner_impact_bias', 'confidence'],
    enums: {
      session_pattern: ['improving', 'stable', 'declining', 'mixed', 'unclear'],
      planner_impact_bias: ['none', 'suppress_progression', 'favor_hold', 'favor_regress', 'note_only']
    },
    arrayFields: []
  },
  select_accessories: {
    required: ['selected'],
    enums: {},
    arrayFields: []
  },
  prescribe_accessory: {
    required: ['sets', 'reps', 'rpe', 'key_cue', 'reason'],
    enums: {},
    arrayFields: []
  }
};

// ─── Validation ──────────────────────────────────────────────────────────────

function validateOutput(mode, obj) {
  const schema = SCHEMAS[mode];
  if (!schema) return { valid: false, reason: 'unknown mode' };

  for (const field of schema.required) {
    if (obj[field] === undefined || obj[field] === null) {
      return { valid: false, reason: `missing field: ${field}` };
    }
  }

  for (const [field, allowed] of Object.entries(schema.enums || {})) {
    if (schema.arrayFields.includes(field)) {
      if (!Array.isArray(obj[field])) {
        return { valid: false, reason: `${field} must be an array` };
      }
      for (const val of obj[field]) {
        if (!allowed.includes(val)) {
          return { valid: false, reason: `invalid ${field} value: "${val}"` };
        }
      }
    } else {
      if (!allowed.includes(obj[field])) {
        return { valid: false, reason: `invalid ${field}: "${obj[field]}"` };
      }
    }
  }

  // prescribe_accessory — validate sets/reps/rpe are present
  if (mode === 'prescribe_accessory') {
    if (!obj.sets || !obj.reps || !obj.rpe) return { valid: false, reason: 'sets, reps, and rpe are required' };
    if (!obj.key_cue || typeof obj.key_cue !== 'string') return { valid: false, reason: 'key_cue must be a string' };
    if (!obj.reason || typeof obj.reason !== 'string') return { valid: false, reason: 'reason must be a string' };
    return { valid: true };
  }

  // select_accessories has its own shape — validate selected array
  if (mode === 'select_accessories') {
    if (!Array.isArray(obj.selected) || obj.selected.length < 1 || obj.selected.length > 3) {
      return { valid: false, reason: 'selected must be an array of 1–3 items' };
    }
    for (const item of obj.selected) {
      if (!item.id || typeof item.id !== 'string') return { valid: false, reason: 'each selected item needs a string id' };
      if (!item.reason || typeof item.reason !== 'string') return { valid: false, reason: 'each selected item needs a string reason' };
    }
    return { valid: true };
  }

  if (typeof obj.confidence !== 'number' || obj.confidence < 0 || obj.confidence > 1) {
    return { valid: false, reason: 'confidence must be a number between 0 and 1' };
  }

  return { valid: true };
}

// ─── System Prompts ──────────────────────────────────────────────────────────

const SYSTEM_PROMPTS = {
  pre_session: `You are a sprint session readiness interpreter.
You receive athlete pre-session notes and readiness slider scores.
Your only job is to classify this data into a structured JSON object.
Do not provide motivation, training advice, or medical guidance.

CONTEXT MODIFIER RULES — scan notes for these first, they change everything:
- "First day back", "off-season", "return from break", "haven't sprinted", "first session back", "end of off-season", "first sprint" → ALWAYS set flat_cns + low_pop. planner_impact_bias = "note_only". Lower times/quality are the EXPECTED baseline, not a regression signal. State this in coach_summary.
- Illness recovery, travel fatigue, poor sleep multiple nights → add fatigue_pattern to risk_flags; use "favor_hold" or "note_only".
- External conditions mentioned (wet track, cold, poor surface, wind) → execution_noise in risk_flags, "note_only" bias.
- High readiness sliders but negative notes → trust the notes. Low sliders + positive notes → trust the notes.
- "Slight" or "a little" qualifiers → tag the flag but lower confidence.

planner_impact_bias logic:
- "note_only" → context explains the data (return from break, conditions); session data is not comparable to normal baseline
- "favor_hold" → athlete is readable but suboptimal; hold current progression
- "favor_regress" → clear injury risk, severe fatigue, or technique breakdown
- "suppress_progression" → everything looks fine but one risk flag warrants caution
- "none" → all clear

coach_summary: 1–2 sentences that NAME the key context modifier explicitly (e.g. "First session back from off-season — CNS output expected to be well below normal baseline."). This is the most important field for downstream interpretation.

Output ONLY valid JSON matching this exact schema, nothing else:
{ "readiness_flags": [...], "risk_flags": [...], "coach_summary": "...", "planner_impact_bias": "...", "confidence": 0.0 }
readiness_flags must be an array using only these values: low_pop | flat_cns | slight_tightness | high_readiness | mentally_sharp | low_motivation
risk_flags must be an array using only these values: tightness_warning | technical_instability | fatigue_pattern | execution_noise | none
planner_impact_bias must be exactly one of: none | suppress_progression | favor_hold | favor_regress | note_only
confidence is a float 0.0–1.0. Default to low values when uncertain.`,

  rep_note: `You are a sprint rep note classifier for a fly-sprint training log.
You receive one athlete note about a single sprint rep.
Your only job is to classify the note into structured tags.
Do not provide training advice or motivational coaching.

TAG MAPPING — match these patterns explicitly:
Mechanics:
- "reaching", "overstriding", "arms out front", "heel first", "arm swing too big" → forced_stride
- "short stride", "choppy", "quick but not long", "not covering ground" → forced_stride
- "heavy", "flat", "no pop", "low", "dead legs", "ground felt slow" → low_bounce
- "tilted", "hunched", "not tall", "leaning", "forward lean too much", "not upright" → posture_loss
- "lost it", "fell apart", "rhythm went", "timing off" → rhythm_loss
- "felt fast", "flew", "snappy" → felt_fast
- "smooth", "easy", "relaxed" → smooth
- "good drive angle", "good projection", "good lean out" → good_projection
- "stiff", "bouncy", "reactive", "elastic" → good_stiffness

CONTEXT MODIFIER RULES — these change planner_impact_bias:
- External conditions (wet track, rain, cold, wind, poor surface, lane issues, grass) → execution_noise in risk_flags, planner_impact_bias = "note_only". Conditions explain variance; do NOT treat as technique regression.
- Tightness, soreness, pull risk → tightness_warning in risk_flags
- Pattern across multiple reps (only inferable from "again", "still", "every rep") → fatigue_pattern
- External condition is the PRIMARY cause of a poor rep → planner_impact_bias = "note_only", never "favor_regress"
- Isolated technique error with no pain → execution_noise or technical_instability, "note_only" or "suppress_progression"
- Repeated breakdown + fatigue cue → "favor_hold"
- Pain, acute tightness, sharp sensation → "favor_regress"

coach_summary: 1 sentence that captures WHAT ACTUALLY HAPPENED including any conditions or context that affect how this rep's data should be read. Don't genericize — name the specific cue mentioned.

Output ONLY valid JSON matching this exact schema, nothing else:
{ "rep_tags": [...], "risk_flags": [...], "coach_summary": "...", "planner_impact_bias": "...", "confidence": 0.0 }
rep_tags must be an array using only these values: felt_fast | rhythm_loss | posture_loss | good_projection | good_stiffness | forced_stride | low_bounce | smooth
risk_flags must be an array using only these values: tightness_warning | technical_instability | fatigue_pattern | execution_noise | none
planner_impact_bias must be exactly one of: none | suppress_progression | favor_hold | favor_regress | note_only
confidence is a float 0.0–1.0. Default to low values when uncertain.`,

  stop_reason_normalize: `You are a sprint session stop-reason classifier.
You receive context about why a sprint session was stopped early.
Your job is to map the stop reason to the closest normalized category.
Do not provide advice. Be conservative — if ambiguous, choose the safest match and lowest-impact bias.

CONTEXT MODIFIER RULES:
- If stop was due to external conditions (weather, surface, rain, heat) → normalized_stop_reason = "planned_cap", risk_flags = ["execution_noise"], planner_impact_bias = "note_only"
- If stop was pre-planned ("only doing 3", "session cap", "as planned") → "planned_cap", planner_impact_bias = "none"
- "Tightness", "pull", "strain", "sharp" → "tightness_warning", planner_impact_bias = "favor_regress"
- Quality drop without pain → "speed_drop" or "rhythm_loss", planner_impact_bias = "favor_hold"
- First session back / return from off-season → low_pop, planner_impact_bias = "note_only" (expected, not pathological)
- coach_summary must name any context modifier that explains the stop.

Output ONLY valid JSON matching this exact schema, nothing else:
{ "normalized_stop_reason": "...", "risk_flags": [...], "coach_summary": "...", "planner_impact_bias": "...", "confidence": 0.0 }
normalized_stop_reason must be exactly one of: speed_drop | rhythm_loss | posture_breakdown | tightness_warning | low_pop | mental_flatness | planned_cap
risk_flags must be an array using only these values: tightness_warning | technical_instability | fatigue_pattern | execution_noise | none
planner_impact_bias must be exactly one of: none | suppress_progression | favor_hold | favor_regress | note_only
confidence is a float 0.0–1.0. Default to low values when uncertain.
coach_summary is at most 1 sentence — name the specific reason and any context modifier.`,

  prescribe_accessory: `You are a sprint performance coach prescribing exact loading parameters for a single accessory exercise.

You receive: the exercise details, the athlete's current session context (issue type, readiness, fatigue, sprint performance notes), and relevant biomechanics research principles.

Your job is to prescribe EXACT sets, reps, and RPE for this specific athlete in this specific session — not generic defaults.

Rules:
- Sets: integer (1–5)
- Reps: string like "6", "4–6", "8–10", or "20s hold" for isometric
- RPE: string like "7", "7–8", or "6–7"
- key_cue: one short technical coaching cue specific to this exercise and the athlete's issue
- reason: 1–2 sentences explaining WHY this prescription fits this session (reference the issue type, fatigue, or research if relevant)

Output ONLY valid JSON, nothing else:
{ "sets": 3, "reps": "6–8", "rpe": "7", "key_cue": "...", "reason": "..." }`,

  select_accessories: `You are selecting accessory exercises for a sprint performance system.

You MUST:
- Choose 2–3 accessories from the provided library
- Base decisions ONLY on: issueType, fatigue level, athlete notes

DO NOT:
- Invent exercises not in the library
- Exceed 3 accessories
- Select redundant exercises (same category)

RULES:
- Prioritize qualities matching issueType
- If fatigue is high → prefer higher CNS score (less taxing)
- Do not select more than 1 from same category
- Always include at least one stiffness OR front_side exercise

Output ONLY valid JSON matching this exact schema, nothing else:
{ "selected": [{ "id": "<library_id>", "reason": "<one sentence>" }] }
You must use exact id values from the library. selected must have 2 or 3 items.`,

  session_summary: `You are a sprint session pattern extractor.
You receive session summary notes from an athlete.
Your job is to identify the primary and secondary issues and the overall session pattern.
Do not provide training advice or progression decisions — a separate deterministic system handles those.

CRITICAL — distinguish session types before classifying:
- Return sessions ("first day back", "off-season", "return from break", "first sprint in weeks") → primary_issue = "first session back from off-season" (or similar). session_pattern = "unclear" (baseline not established). planner_impact_bias = "note_only". Data from this session is NOT comparable to pre-break baseline.
- Condition-affected sessions (wet, cold, wind, poor surface) → primary_issue should name the condition. planner_impact_bias = "note_only" if conditions clearly explain performance.
- Normal sessions with athlete-driven decline → session_pattern = "declining", planner_impact_bias = "favor_hold" or "favor_regress" based on severity.

planner_impact_bias:
- "note_only" → context (return from break, conditions) explains the data; don't act on it as a normal signal
- "favor_hold" → session showed meaningful issue but athlete is OK
- "favor_regress" → injury risk or significant breakdown
- "suppress_progression" → session was fine but one flag warrants caution
- "none" → clean session, no flags

coach_summary: 2 sentences max. MUST name any context modifiers (return from break, conditions) that affect how session data should be interpreted downstream. This summary is read by a planner that needs to know if this session is an outlier.

Output ONLY valid JSON matching this exact schema, nothing else:
{ "primary_issue": "...", "secondary_issue": "...", "session_pattern": "...", "coach_summary": "...", "planner_impact_bias": "...", "confidence": 0.0 }
primary_issue: short phrase describing the main limiting factor or context modifier (e.g. "first session back from off-season", "fatigue from rep 2", "wet track — execution noise", "no clear issue")
secondary_issue: short phrase or empty string ""
session_pattern must be exactly one of: improving | stable | declining | mixed | unclear
planner_impact_bias must be exactly one of: none | suppress_progression | favor_hold | favor_regress | note_only
confidence is a float 0.0–1.0. Default to low values when uncertain.`
};

// ─── User Message Builder ────────────────────────────────────────────────────

function buildUserMessage(mode, text, context) {
  switch (mode) {
    case 'pre_session':
      return `Athlete notes: "${text || '(none)'}"\nReadiness scores — Leg Freshness: ${context.legFreshness ?? '?'}/10, General Freshness: ${context.generalFreshness ?? '?'}/10, Energy: ${context.energy ?? '?'}/10, Bad Sleep: ${context.badSleep ? 'yes' : 'no'}`;

    case 'rep_note':
      return `Rep ${context.repNum || '?'} note: "${text || '(none)'}"\nRep scores — Quality: ${context.quality ?? '?'}/10, Ease: ${context.ease ?? '?'}/10, Rhythm: ${context.rhythm ?? '?'}/10, Confidence: ${context.confidence ?? '?'}/10`;

    case 'stop_reason_normalize':
      return `Session stopped after ${context.repCount || '?'} reps.\nLast rep notes: "${text || '(none)'}"\nRep quality scores this session: ${context.repQualities || '(unavailable)'}`;

    case 'session_summary':
      return `Best part of session: "${context.bestPart || '(none)'}"\nBreakdown point: "${context.breakdownPoint || '(none)'}"\nOther notes: "${text || '(none)'}"\nSession verdict (deterministic analyzer): ${context.sessionVerdict || 'unknown'}\nReps completed: ${context.repCount ?? '?'}, Stop triggered: ${context.stopTriggered ? 'yes' : 'no'}`;

    case 'select_accessories': {
      const lib = (context.library || []).map(ex =>
        `ID: ${ex.id} | ${ex.name} | category: ${ex.category} | cns: ${ex.cns} | qualities: ${ex.qualities.join(', ')} | redundancy: ${ex.redundancy} | loadability: ${ex.loadability}`
      ).join('\n');
      return `Issue Type: ${context.issueType || 'none'}\nFatigue Level: ${context.fatigue || 'normal'}\nAthlete Notes: ${text || '(none)'}\n\nACCESSORY LIBRARY:\n${lib}`;
    }

    case 'prescribe_accessory': {
      const ex = context.exercise || {};
      const principles = (context.principles || [])
        .map(p => `- ${p.title || p.id}: ${p.summary || p.sprint_implication || ''}`)
        .join('\n');
      const sessionLines = [
        `Exercise: ${ex.name} | Category: ${ex.category} | CNS load: ${ex.cns} | Qualities: ${(ex.qualities || []).join(', ')}`,
        `Issue type this session: ${context.issueType || 'none'}`,
        `Fatigue level: ${context.fatigue || 'normal'}`,
        `Readiness — Leg freshness: ${context.legFreshness ?? '?'}/10, Energy: ${context.energy ?? '?'}/10`,
        `Progression decision: ${context.progressionDecision || 'hold'}`,
        `Athlete notes: ${text || '(none)'}`,
      ];
      if (principles) sessionLines.push(`\nRelevant research principles:\n${principles}`);
      return sessionLines.join('\n');
    }

    default:
      return text || '';
  }
}

// ─── Repair Prompt ───────────────────────────────────────────────────────────

function buildRepairPrompt(badOutput, validationReason) {
  return `Your previous response failed validation: ${validationReason}
The broken output was:
${JSON.stringify(badOutput)}

Fix ONLY the invalid fields and return valid JSON.
All field names, types, and enum values must match the schema exactly.
Return ONLY the corrected JSON object, no other text.`;
}

// ─── OpenRouter Call ─────────────────────────────────────────────────────────

async function callOpenRouter(systemPrompt, userMessage, timeoutMs = 8000, modelOverride = null) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${OR_BASE}/chat/completions`, {
      signal: controller.signal,
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`,
        'Content-Type': 'application/json',
        'HTTP-Referer': 'http://localhost:3001',
        'X-Title': 'Sprint Lab'
      },
      body: JSON.stringify({
        model: modelOverride || MODEL,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userMessage }
        ],
        temperature: 0.1,
        max_tokens: 300,
        response_format: { type: 'json_object' }
      })
    });

    clearTimeout(timeout);

    if (res.status === 401) {
      throw Object.assign(new Error('Invalid API key'), { code: 'AUTH_ERROR' });
    }
    if (res.status === 402) {
      throw Object.assign(new Error('Insufficient credits'), { code: 'CREDITS_ERROR' });
    }
    if (res.status === 400) {
      const body = await res.json().catch(() => ({}));
      throw Object.assign(new Error(body?.error?.message || 'Bad request — check model name'), { code: 'MODEL_ERROR' });
    }
    if (!res.ok) {
      throw Object.assign(new Error(`OpenRouter HTTP ${res.status}`), { code: 'API_ERROR' });
    }

    const data = await res.json();
    const content = data?.choices?.[0]?.message?.content;
    if (!content) {
      throw Object.assign(new Error('Empty response from model'), { code: 'EMPTY_RESPONSE' });
    }

    // Claude sometimes wraps JSON in markdown code fences — strip them
    let cleaned = content.trim();
    if (cleaned.startsWith('```')) {
      cleaned = cleaned.replace(/^```(?:json)?\s*/i, '').replace(/\s*```\s*$/, '').trim();
    }

    return JSON.parse(cleaned);
  } catch (err) {
    clearTimeout(timeout);
    if (err.name === 'AbortError') {
      throw Object.assign(new Error('Request timed out'), { code: 'TIMEOUT' });
    }
    throw err;
  }
}

// ─── Route ───────────────────────────────────────────────────────────────────

app.post('/api/ai/interpret', async (req, res) => {
  if (!API_KEY) {
    return res.status(500).json({ error: 'OPENROUTER_API_KEY is not configured', code: 'NO_KEY' });
  }

  const { mode, text, ...context } = req.body;

  if (!SCHEMAS[mode]) {
    return res.status(400).json({ error: `Unknown mode: "${mode}"`, code: 'INVALID_MODE' });
  }

  const systemPrompt = SYSTEM_PROMPTS[mode];
  const userMessage = buildUserMessage(mode, text, context);
  const modelOverride = mode === 'prescribe_accessory' ? 'anthropic/claude-sonnet-4-6' : null;

  try {
    // First attempt
    let output = await callOpenRouter(systemPrompt, userMessage, 8000, modelOverride);
    let validation = validateOutput(mode, output);

    if (!validation.valid) {
      // Single repair attempt
      const repairMessage = buildRepairPrompt(output, validation.reason);
      output = await callOpenRouter(systemPrompt, repairMessage, 6000, modelOverride);
      validation = validateOutput(mode, output);

      if (!validation.valid) {
        return res.status(422).json({
          error: 'Schema validation failed after repair attempt',
          code: 'PARSE_FAILURE',
          detail: validation.reason
        });
      }
    }

    return res.json({ ok: true, mode, output });

  } catch (err) {
    const status =
      err.code === 'AUTH_ERROR'    ? 401 :
      err.code === 'CREDITS_ERROR' ? 402 :
      err.code === 'TIMEOUT'       ? 504 : 502;

    return res.status(status).json({ error: err.message, code: err.code || 'API_ERROR' });
  }
});

// ─── Research DB ─────────────────────────────────────────────────────────────

const RESEARCH_PATH = path.join(__dirname, 'spos_starter', 'spos_starter', 'outputs', 'biomechanics_principles.json');

app.get('/api/research', (req, res) => {
  if (!fs.existsSync(RESEARCH_PATH)) {
    return res.json({ ok: false, data: null, code: 'NO_RESEARCH_DB' });
  }
  try {
    const data = JSON.parse(fs.readFileSync(RESEARCH_PATH, 'utf8'));
    res.json({ ok: true, data });
  } catch (err) {
    res.status(500).json({ error: 'Failed to parse research DB', code: 'PARSE_ERROR' });
  }
});

// ─── Start ────────────────────────────────────────────────────────────────────

app.listen(PORT, () => {
  if (!API_KEY) {
    console.warn('[Sprint Lab] WARNING: No API key found (OPENROUTER_API_KEY or OPENAI_API_KEY). AI features will be disabled.');
  }
  console.log(`[Sprint Lab] Server running at http://localhost:${PORT}`);
  console.log(`[Sprint Lab] Model: ${MODEL}`);
  console.log('[Sprint Lab] Open http://localhost:' + PORT + ' in your browser');
});
