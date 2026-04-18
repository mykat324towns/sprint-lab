# Sprint Program Status — 2026-04-16

## Done
- Limiter research complete — leg stiffness + touchdown timing are co-primary
- Phase 0 program written — protocol, weekly structure, lift days, stop/progression rules
- Session analyzer audited — 4 HIGH bugs found, not yet fixed

## Blocked
- App logic bugs unfixed → wrong prescriptions if used now
- No sessions logged yet
- Notion export not run
- Session review workflow untested

## Bugs (fix before using app)
- 3/3 perfect reps at ceiling=5 → wrongly rated "acceptable" not "strong"
- Fly progression gate requires `ceilingReps >= 6` → impossible in Phase 0
- Docs say 2 consecutive strong sessions; logic requires 3
- Any degraded session regresses reps — no external-condition override

## Next
1. Fix analyzer bugs OR run Session 1 manually (bugs only bite when app scores sessions)
2. Session 1 → confirms stiffness vs. touchdown timing as primary limiter
3. First pass through session review workflow
4. Export to Notion

## Key decision
Fix bugs first, or log Session 1 by hand in the interim?

## Links
- [[phase0_notes]] — full program
- [[research/notes]] — limiter analysis
- [[sessions/logs]] — empty
