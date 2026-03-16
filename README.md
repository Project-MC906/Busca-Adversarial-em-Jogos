# Damas Brasileiras - Adversarial Search Playground

This project implements Brazilian Checkers (Damas) with adversarial search and multiple evaluation heuristics.

The main goal of this README is to help you:
- change evaluation constants (piece values, positional bonuses, heuristic weights),
- run controlled games between equal or different heuristics,
- compare results using generated logs.

## 1. Quick Setup

Requirements:
- Python 3.10+

Install dependencies:

```bash
pip install -r requirements.txt
```

Run CLI help:

```bash
python main.py -h
python main.py play -h
```

## 2. Available Heuristics

Heuristics are selected by ID in `main.py`:
- `h1` -> `heuristics/material.py::evaluate_material`
- `h2` -> `heuristics/positional.py::evaluate_positional`
- `h3` -> `heuristics/full.py::evaluate_full`
- `h4` -> `heuristics/connectivity.py::evaluate_connectivity`

Mapping is defined in `main.py` inside `_get_evaluator`.

## 3. Where to Change Constants and Weights

### Global game/evaluation constants

Edit `game/constants.py`:
- `PIECE_VALUE`
- `KING_VALUE`
- `DRAW_MOVE_LIMIT`
- Positional terms used by `h2`:
  - `CENTER_BONUS`
  - `EDGE_BONUS`
  - `ADVANCE_BONUS_PER_ROW`

These values affect all heuristics that depend on material/position.

### Heuristic-specific weights

Edit each file directly:

- `heuristics/full.py` (`h3`):
  - `MOBILITY_WEIGHT`

- `heuristics/connectivity.py` (`h4`):
  - `SUPPORT_BONUS`
  - `ISOLATION_PENALTY`
  - `THREAT_BONUS`
  - `MATERIAL_WEIGHT`

`h1` and `h2` mostly depend on constants in `game/constants.py`.

## 4. Play Single Games

### Human vs AI (terminal)

```bash
python main.py play --mode human_vs_ai --heuristic h3 --time 1.0
```

### Human vs AI (GUI)

```bash
python main.py play --mode human_vs_ai --heuristic h3 --time 1.0 --gui
```

### AI vs AI (same heuristic on both sides)

```bash
python main.py play --mode ai_vs_ai --white h3 --black h3 --time 1.0
```

### AI vs AI (different heuristics)

```bash
python main.py play --mode ai_vs_ai --white h4 --black h2 --time 1.0
```

### Save detailed game logs

Add `--log` to `play`:

```bash
python main.py play --mode ai_vs_ai --white h3 --black h2 --time 1.0 --log
```

Logs are saved under `logs/games/` (`.json`, `_summary.csv`, `_moves.csv`).

## 5. Run Experiment Batches

### Internal tournament from `main.py tournament`

```bash
python main.py tournament --games 20 --time 1.0
```

Important:
- this command currently compares only `h1`, `h2`, and `h3`.
- it alternates colors to reduce first-move bias.
- it logs tournament data by default to `logs/tournaments/`.

### Full experiment suite

```bash
python main.py experiments --games 10 --time 1.0
```

This runs:
- Minimax vs Alpha-Beta node comparison,
- heuristic round-robin (includes `h4` in `experiments/analysis.py`),
- TT impact,
- vs-random baseline,
- node comparison plot (`nodes_comparison.png` if matplotlib is available).

## 6. Suggested Workflow for Tuning

Use this loop for reproducible comparisons:

1. Pick one baseline configuration (for example current `h3`).
2. Change one parameter at a time (example: increase `MOBILITY_WEIGHT` from 3 to 5).
3. Run a fixed-size matchup with fixed `--time` (for example 20 to 50 games).
4. Compare win rate and efficiency metrics (depth, nodes per move, time per move).
5. Keep only changes that improve both strength and stability.

Example protocol:

```bash
# Before change
python main.py play --mode ai_vs_ai --white h3 --black h3 --time 1.0 --log
python main.py tournament --games 20 --time 1.0

# After changing constants/weights
python main.py play --mode ai_vs_ai --white h3 --black h3 --time 1.0 --log
python main.py tournament --games 20 --time 1.0
```

For stronger evidence, repeat with larger `--games` (for example 50 or 100).

## 7. Adding a New Heuristic (h5, optional)

1. Create `heuristics/my_new_heuristic.py` with `evaluate_my_new_heuristic(state)`.
2. Register it in `_get_evaluator` in `main.py`.
3. Add the new ID to CLI choices in `build_parser()` (`--heuristic`, `--white`, `--black`).
4. Optionally include it in `cmd_tournament` and `experiments/analysis.py` round-robin.

## 8. Useful Files

- `main.py`: CLI entrypoint and heuristic selection.
- `game/constants.py`: board and scoring constants.
- `heuristics/material.py`: `h1`.
- `heuristics/positional.py`: `h2`.
- `heuristics/full.py`: `h3`.
- `heuristics/connectivity.py`: `h4`.
- `experiments/tournament.py`: match runner + aggregation.
- `experiments/analysis.py`: experiment suite.
- `experiments/logger.py`: JSON/CSV log writer.

## 9. Notes

- In this codebase, positive score means advantage for White.
- Time limit is per move (`--time`).
- If you tune evaluation values, prefer comparing many games rather than a single run.