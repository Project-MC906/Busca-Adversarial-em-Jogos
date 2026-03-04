"""
Heurística h1 — Material puro.

Avaliação mais simples possível: apenas diferença de material.
  peça comum = 100, dama = 300  (constantes de PIECE_VALUE e KING_VALUE)

Positivo → vantagem das brancas (maximizador).
Retorna 0 em estados terminais (a utilidade é tratada separadamente).
"""

from __future__ import annotations

from game.state import GameState
from heuristics.weights import PIECE_VALUE, KING_VALUE
from game.bitboard import popcount


def evaluate_material(state: GameState) -> int:
    """
    h1: Diferencial puro de material.

    score = (peças_brancas × PIECE_VALUE + damas_brancas × KING_VALUE)
          - (peças_pretas  × PIECE_VALUE + damas_pretas  × KING_VALUE)

    Damas contam KING_VALUE em vez de PIECE_VALUE (não são somadas).
    """
    kings    = state.kings_bb
    white_bb = state.white_bb
    black_bb = state.black_bb

    white_kings  = popcount(white_bb & kings)
    white_pieces = popcount(white_bb) - white_kings

    black_kings  = popcount(black_bb & kings)
    black_pieces = popcount(black_bb) - black_kings

    white_score = white_pieces * PIECE_VALUE + white_kings * KING_VALUE
    black_score = black_pieces * PIECE_VALUE + black_kings * KING_VALUE

    return white_score - black_score
