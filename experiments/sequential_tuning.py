"""
Experimento sequencial de tuning da heuristica posicional (h2).

Fases (isoladas):
1) criterio de centralidade
2) pesos de pecas
3) necessidade do criterio de borda
4) bonus de avanco

Cada fase usa o melhor resultado da fase anterior e altera apenas um fator.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from experiments.analysis import make_id_agent
from experiments.tournament import aggregate_metrics, run_tournament
from game.bitboard import iter_bits, popcount, test_bit
from game.constants import BIT_TO_ROWCOL, CENTER_BITS, FOUR_CENTER_BITS, SIX_CENTER_BITS, EIGHT_CENTER_BITS, EDGE_COLS, WHITE, BLACK
from game.state import GameState


@dataclass(frozen=True)
class HeuristicParams:
    piece_value: int = 100
    king_value: int = 300
    center_bonus: int = 10
    edge_bonus: int = 5
    advance_bonus_per_row: int = 5
    centrality_mode: str = "core8"


def _extended_center_bits() -> frozenset[int]:
    bits: set[int] = set(CENTER_BITS)
    for sq, (row, col) in BIT_TO_ROWCOL.items():
        if 2 <= row <= 5 and 1 <= col <= 6:
            bits.add(sq)
    return frozenset(bits)


EXTENDED_CENTER_BITS = _extended_center_bits()


def _distance_center_value(sq: int, base_bonus: int) -> int:
    row, col = BIT_TO_ROWCOL[sq]
    dr = abs(row - 3.5)
    dc = abs(col - 3.5)
    dist = dr + dc
    max_dist = 7.0
    scale = max(0.0, 1.0 - (dist / max_dist))
    return int(round(base_bonus * scale))


def _advance_score(bb: int, kings_bb: int, player: int, advance_bonus_per_row: int) -> int:
    score = 0
    for sq in iter_bits(bb):
        if test_bit(kings_bb, sq):
            continue
        row, _ = BIT_TO_ROWCOL[sq]
        if player == WHITE:
            advance = max(0, 7 - row - 2)
        else:
            advance = max(0, row - 2)
        score += advance * advance_bonus_per_row
    return score


def _center_score(bb: int, mode: str, center_bonus: int) -> int:
    score = 0
    if mode == "four":
        for sq in iter_bits(bb):
            if sq in FOUR_CENTER_BITS:
                score += center_bonus
        return score
    if mode == "six":
        for sq in iter_bits(bb):
            if sq in SIX_CENTER_BITS:
                score += center_bonus
        return score
    if mode == "eight":
        for sq in iter_bits(bb):
            if sq in EIGHT_CENTER_BITS:
                score += center_bonus
        return score
    if mode == "core8":
        for sq in iter_bits(bb):
            if sq in CENTER_BITS:
                score += center_bonus
        return score
    if mode == "extended12":
        half = max(1, center_bonus // 2)
        for sq in iter_bits(bb):
            if sq in CENTER_BITS:
                score += center_bonus
            elif sq in EXTENDED_CENTER_BITS:
                score += half
        return score
    if mode == "distance":
        for sq in iter_bits(bb):
            score += _distance_center_value(sq, center_bonus)
        return score
    raise ValueError(f"centrality_mode invalido: {mode}")


def _edge_score(bb: int, edge_bonus: int) -> int:
    if edge_bonus == 0:
        return 0
    score = 0
    for sq in iter_bits(bb):
        _, col = BIT_TO_ROWCOL[sq]
        if col in EDGE_COLS:
            score += edge_bonus
    return score


def make_parametrized_positional_evaluator(params: HeuristicParams):
    def evaluate(state: GameState) -> int:
        kings = state.kings_bb
        w_bb = state.white_bb
        b_bb = state.black_bb

        w_kings = popcount(w_bb & kings)
        b_kings = popcount(b_bb & kings)
        w_pieces = popcount(w_bb) - w_kings
        b_pieces = popcount(b_bb) - b_kings

        material = (
            w_pieces * params.piece_value
            + w_kings * params.king_value
            - b_pieces * params.piece_value
            - b_kings * params.king_value
        )

        w_adv = _advance_score(w_bb, kings, WHITE, params.advance_bonus_per_row)
        b_adv = _advance_score(b_bb, kings, BLACK, params.advance_bonus_per_row)
        w_ctr = _center_score(w_bb, params.centrality_mode, params.center_bonus)
        b_ctr = _center_score(b_bb, params.centrality_mode, params.center_bonus)
        w_edg = _edge_score(w_bb, params.edge_bonus)
        b_edg = _edge_score(b_bb, params.edge_bonus)

        return material + (w_adv - b_adv) + (w_ctr - b_ctr) + (w_edg - b_edg)

    return evaluate


def run_stage(
    stage_name: str,
    variants: dict[str, HeuristicParams],
    time_limit: float,
    num_games: int,
):
    names = list(variants.keys())
    agents = {
        name: make_id_agent(
            evaluator=make_parametrized_positional_evaluator(params),
            time_limit=time_limit,
        )
        for name, params in variants.items()
    }

    table = {
        name: {
            "points": 0.0,
            "wins": 0,
            "losses": 0,
            "draws": 0,
            "games": 0,
            "avg_depth": 0.0,
            "avg_nodes_per_move": 0.0,
            "avg_time_per_move_s": 0.0,
        }
        for name in names
    }

    print(f"\n=== {stage_name} ===")
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a = names[i]
            b = names[j]
            result = run_tournament(
                agents[a],
                agents[b],
                name_a=a,
                name_b=b,
                num_games=num_games,
                progress=True,
                log_tournament=False,
            )
            agg = aggregate_metrics(result.all_results)
            print(result.summary())
            print(
                f"  depth={agg['avg_depth']:.2f} | "
                f"nodes/mov={agg['avg_nodes_per_move']:.1f} | "
                f"tempo/mov={agg['avg_time_per_move_s']:.3f}s"
            )

            table[a]["wins"] += result.wins_a
            table[a]["losses"] += result.wins_b
            table[a]["draws"] += result.draws
            table[a]["games"] += result.total_games
            table[a]["points"] += result.wins_a + 0.5 * result.draws

            table[b]["wins"] += result.wins_b
            table[b]["losses"] += result.wins_a
            table[b]["draws"] += result.draws
            table[b]["games"] += result.total_games
            table[b]["points"] += result.wins_b + 0.5 * result.draws

            table[a]["avg_depth"] += agg["avg_depth"]
            table[a]["avg_nodes_per_move"] += agg["avg_nodes_per_move"]
            table[a]["avg_time_per_move_s"] += agg["avg_time_per_move_s"]
            table[b]["avg_depth"] += agg["avg_depth"]
            table[b]["avg_nodes_per_move"] += agg["avg_nodes_per_move"]
            table[b]["avg_time_per_move_s"] += agg["avg_time_per_move_s"]

    pairings_per_variant = max(1, len(names) - 1)
    for name in names:
        table[name]["avg_depth"] /= pairings_per_variant
        table[name]["avg_nodes_per_move"] /= pairings_per_variant
        table[name]["avg_time_per_move_s"] /= pairings_per_variant

    ordered = sorted(
        table.items(),
        key=lambda kv: (
            kv[1]["points"],
            kv[1]["wins"],
            -kv[1]["losses"],
        ),
        reverse=True,
    )

    print("\nRanking da fase:")
    for idx, (name, row) in enumerate(ordered, start=1):
        print(
            f"{idx:>2}. {name:<16} "
            f"pts={row['points']:.1f} "
            f"W={row['wins']} L={row['losses']} D={row['draws']} "
            f"depth={row['avg_depth']:.2f} nodes/mov={row['avg_nodes_per_move']:.1f}"
        )

    winner_name = ordered[0][0]
    return winner_name, variants[winner_name], table


def run_sequential_tuning(num_games: int, time_limit: float, output_path: str):
    base = HeuristicParams()

    stage_results = {}

    stage1_variants = {
        "four": replace(base, centrality_mode="four"),
        "six": replace(base, centrality_mode="six"),
        "eight": replace(base, centrality_mode="eight"),
        "core8": replace(base, centrality_mode="core8"),
        "extended12": replace(base, centrality_mode="extended12"),
        "distance": replace(base, centrality_mode="distance"),
    }
    winner1_name, best1, table1 = run_stage(
        "Fase 1 - Criterio de centralidade",
        stage1_variants,
        time_limit,
        num_games,
    )
    stage_results["stage1_centrality"] = {
        "winner": winner1_name,
        "winner_params": asdict(best1),
        "table": table1,
    }

    stage2_variants = {
        "pv80_kv240": replace(best1, piece_value=80, king_value=240),
        "pv100_kv300": replace(best1, piece_value=100, king_value=300),
        "pv120_kv360": replace(best1, piece_value=120, king_value=360),
        "pv100_kv250": replace(best1, piece_value=100, king_value=250),
        "pv100_kv350": replace(best1, piece_value=100, king_value=350),
    }
    winner2_name, best2, table2 = run_stage(
        "Fase 2 - Pesos das pecas",
        stage2_variants,
        time_limit,
        num_games,
    )
    stage_results["stage2_piece_weights"] = {
        "winner": winner2_name,
        "winner_params": asdict(best2),
        "table": table2,
    }

    stage3_variants = {
        "edge_off": replace(best2, edge_bonus=0),
        "edge_on": replace(best2, edge_bonus=5),
    }
    winner3_name, best3, table3 = run_stage(
        "Fase 3 - Necessidade de borda",
        stage3_variants,
        time_limit,
        num_games,
    )
    stage_results["stage3_edge_criterion"] = {
        "winner": winner3_name,
        "winner_params": asdict(best3),
        "table": table3,
    }

    stage4_variants = {
        "adv0": replace(best3, advance_bonus_per_row=0),
        "adv3": replace(best3, advance_bonus_per_row=3),
        "adv5": replace(best3, advance_bonus_per_row=5),
        "adv7": replace(best3, advance_bonus_per_row=7),
        "adv10": replace(best3, advance_bonus_per_row=10),
    }
    winner4_name, best4, table4 = run_stage(
        "Fase 4 - Bonus de avanco",
        stage4_variants,
        time_limit,
        num_games,
    )
    stage_results["stage4_advance_bonus"] = {
        "winner": winner4_name,
        "winner_params": asdict(best4),
        "table": table4,
    }

    print("\n=== Parametros finais recomendados ===")
    print(best4)

    payload = {
        "num_games_per_pairing": num_games,
        "time_limit_s": time_limit,
        "final_recommendation": asdict(best4),
        "stages": stage_results,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRelatorio salvo em: {out}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Tuning sequencial da heuristica posicional")
    parser.add_argument("--games", type=int, default=20, help="Jogos por confronto")
    parser.add_argument("--time", type=float, default=0.1, help="Tempo por jogada (segundos)")
    parser.add_argument(
        "--output",
        type=str,
        default="logs/experiments/sequential_tuning_results.json",
        help="Caminho do JSON de saida",
    )
    return parser


def main():
    args = build_parser().parse_args()
    run_sequential_tuning(num_games=args.games, time_limit=args.time, output_path=args.output)


if __name__ == "__main__":
    main()
