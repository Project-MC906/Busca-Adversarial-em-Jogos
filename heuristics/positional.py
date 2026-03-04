"""
Heurística h2 — Posicional.

Combina:
  (1) Material (heurística h1)
  (2) Bônus de avanço  — pedras comuns mais próximas da promoção valem mais.
  (3) Controle de centro — peças nas casas centrais ganham bônus.
  (4) Segurança de borda — peças nas colunas laterais são mais difíceis de capturar.
"""

from __future__ import annotations

from game.state import GameState
from game.constants import (
    WHITE, BLACK,
    CENTER_BITS,
    EDGE_COLS,
    BIT_TO_ROWCOL,
)
from heuristics.weights import (
    PIECE_VALUE, KING_VALUE,
    CENTER_BONUS,
    EDGE_BONUS,
    ADVANCE_BONUS_PER_ROW,
)
from typing import Optional
from game.bitboard import iter_bits, popcount, test_bit
from heuristics.material import evaluate_material


def _advance_score(bb: int, kings_bb: int, player: int, bonus_per_row: int = ADVANCE_BONUS_PER_ROW) -> int:
    """
    Bônus de avanço para pedras comuns na direção da promoção.
    Brancas avançam de row 7 → row 0; pretas de row 0 → row 7.
    O bônus é proporcional à distância percorrida desde a fileira inicial.
    """
    score = 0
    for sq in iter_bits(bb):
        if test_bit(kings_bb, sq):
            continue  # damas já têm KING_VALUE
        row, _ = BIT_TO_ROWCOL[sq]
        if player == WHITE:
            # brancas começam em row 5-7, avançam para row 0
            # bônus = (7 - row) dá 0 para row 7, +7 para row 0
            advance = max(0, 7 - row - 2)  # primeiras 2 rows não bonificadas
        else:
            # pretas começam em row 0-2, avançam para row 7
            advance = max(0, row - 2)
        score += advance * bonus_per_row
    return score


def _center_score(bb: int, center_bonus: int = CENTER_BONUS) -> int:
    """Bônus para peças nas casas centrais."""
    score = 0
    for sq in iter_bits(bb):
        if sq in CENTER_BITS:
            score += center_bonus
    return score


def _edge_score(bb: int, edge_bonus: int = EDGE_BONUS) -> int:
    """Bônus para peças nas bordas laterais (mais seguras)."""
    score = 0
    for sq in iter_bits(bb):
        _, col = BIT_TO_ROWCOL[sq]
        if col in EDGE_COLS:
            score += edge_bonus
    return score


def evaluate_positional(
    state: GameState,
    center_bonus: int = CENTER_BONUS,
    edge_bonus: int = EDGE_BONUS,
    advance_bonus_per_row: int = ADVANCE_BONUS_PER_ROW,
) -> int:
    """
    h2: Material + Avanço + Centro + Segurança de borda.

    Aceita pesos opcionais para que outras heurísticas (ex: h3) possam
    reutilizar esta função com seus próprios valores de configuração.
    """
    mat   = evaluate_material(state)

    kings = state.kings_bb
    w_bb  = state.white_bb
    b_bb  = state.black_bb

    # Avanço de pedras comuns
    w_adv = _advance_score(w_bb, kings, WHITE, advance_bonus_per_row)
    b_adv = _advance_score(b_bb, kings, BLACK, advance_bonus_per_row)

    # Controle de centro
    w_ctr = _center_score(w_bb, center_bonus)
    b_ctr = _center_score(b_bb, center_bonus)

    # Segurança de borda
    w_edg = _edge_score(w_bb, edge_bonus)
    b_edg = _edge_score(b_bb, edge_bonus)

    return (
        mat
        + (w_adv - b_adv)
        + (w_ctr - b_ctr)
        + (w_edg - b_edg)
    )
