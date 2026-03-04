"""
Heurística h4 — Conectividade e Ameaças Imediatas.

Filosofia distinta de h1/h2/h3: em vez de contar material ou posição,
avalia COMO as peças trabalham em equipe:

  (1) Conectividade — cada peça com ao menos um vizinho diagonal amigo
      recebe SUPPORT_BONUS (peças apoiadas são mais difíceis de capturar).
  (2) Isolamento     — peças sem nenhum vizinho amigo recebem ISOLATION_PENALTY.
  (3) Ameaça imediata— bônus por cada peça inimiga que pode ser capturada
      no próximo lance (pressão tática imediata).
  (4) Material leve  — pequeno peso de material como desempate.

Ideia: preferencia por posições em que as peças estão agrupadas e
ameaçam capturas, mesmo que isso sacrifique vantagem posicional.
"""

from __future__ import annotations

from game.state import GameState
from game.constants import (
    WHITE, BLACK,
    PIECE_VALUE, KING_VALUE,
    NEIGHBORS, ALL_DIRS,
    BIT_TO_ROWCOL,
)
from game.bitboard import iter_bits, popcount, test_bit
from game.moves import generate_moves
from heuristics.weights import (
    PIECE_VALUE, KING_VALUE,
    SUPPORT_BONUS,
    ISOLATION_PENALTY,
    THREAT_BONUS,
    MATERIAL_WEIGHT_H4,
)


def _connectivity_score(own_bb: int, enemy_bb: int) -> int:
    """
    Para cada peça em own_bb, conta quantos vizinhos diagonais
    também pertencem a own_bb (apoio mútuo).
    """
    score = 0
    for sq in iter_bits(own_bb):
        support = 0
        for d in ALL_DIRS:
            nb = NEIGHBORS[sq][d]
            if nb is not None and test_bit(own_bb, nb):
                support += 1
        if support > 0:
            score += support * SUPPORT_BONUS
        else:
            score -= ISOLATION_PENALTY
    return score


def _threat_count(own_bb: int, enemy_bb: int, kings_bb: int, player: int) -> int:
    """
    Conta quantas peças inimigas distintas podem ser capturadas
    pelos movimentos legais imediatos do jogador `player`.
    """
    moves = generate_moves(own_bb, enemy_bb, kings_bb, player)
    threatened: set[int] = set()
    for m in moves:
        for cap in m.captured:
            threatened.add(cap)
    return len(threatened)


def evaluate_connectivity(state: GameState) -> int:
    """
    h4: Conectividade + Ameaças Imediatas + Material leve.

    Placar do ponto de vista de brancas (positivo = vantagem branca).
    """
    w_bb = state.white_bb
    b_bb = state.black_bb
    k_bb = state.kings_bb

    # (1) + (2) Conectividade / Isolamento
    w_conn = _connectivity_score(w_bb, b_bb)
    b_conn = _connectivity_score(b_bb, w_bb)

    # (3) Ameaças imediatas
    w_threats = _threat_count(w_bb, b_bb, k_bb, WHITE)
    b_threats = _threat_count(b_bb, w_bb, k_bb, BLACK)

    threat_score = (w_threats - b_threats) * THREAT_BONUS

    # (4) Material leve como desempate
    w_kings  = popcount(w_bb & k_bb)
    w_pieces = popcount(w_bb) - w_kings
    b_kings  = popcount(b_bb & k_bb)
    b_pieces = popcount(b_bb) - b_kings

    material = (
        (w_pieces * PIECE_VALUE + w_kings * KING_VALUE)
        - (b_pieces * PIECE_VALUE + b_kings * KING_VALUE)
    )

    return int((w_conn - b_conn) + threat_score + MATERIAL_WEIGHT_H4 * material)
