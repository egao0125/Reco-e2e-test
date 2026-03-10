# Skill: Run Autonomous Optimization

## Purpose
Execute the OBSERVE → DIAGNOSE → HYPOTHESIZE → PLAN → TEST → EVALUATE loop.

## Prerequisites
- Layer 1 (caller/) operational — can make test calls
- Layer 2 (scoring/) operational — can auto-score calls
- Baseline scores established (minimum 1 week of data)

## Loop

1. **OBSERVE:** Read `scores/scores.jsonl`, aggregate last 24h
2. **DIAGNOSE:** Which of the 3 goals is furthest from target?
3. **HYPOTHESIZE:** What change would improve it? Choose from 3 axes:
   - Axis 1: Parameter tuning (config values)
   - Axis 2: Model/provider switch (requires offline eval first)
   - Axis 3: Architecture change (enable/disable pipeline modules)
4. **PLAN:** Generate `configs/candidate_config.json` with exactly 1 change
5. **TEST:** Run test calls with candidate config via Layer 1
6. **EVALUATE:** Compare candidate vs current scores (min 400 calls each)
7. **DECIDE:** Adopt (replace current_config) or reject
8. **LOG:** Record in `experiments/experiments.tsv`

## Safety
- Never change 2+ knobs simultaneously
- Hallucination increase = immediate reject
- Rollback threshold breach = revert to previous config without human approval

## Reference
Read `DESIGN.md` Section 5 and `context_prompt.md` for full details.
