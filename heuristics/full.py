"""
Heurística h3.

Combina:
  (1) h2 (Material + Posicional)
  (2) Mobilidade — diferença no número de movimentos legais disponíveis.
      Privar o adversário de movimentos leva à vitória (asfixia posicional).

É mais custosa que h2 pois precisa gerar movimentos para o adversário.
"""

from __future__ import annotations

from game.state import GameState
from game.constants import WHITE, BLACK
from game.moves import generate_moves
from heuristics.positional import evaluate_positional
from heuristics.weights import (
    MOBILITY_WEIGHT,
    CENTER_BONUS_H3,
    EDGE_BONUS_H3,
    ADVANCE_BONUS_PER_ROW_H3,
)


def evaluate_full(state: GameState) -> int:
    """
    h3: h2 + Mobilidade.

    mobility_score = MOBILITY_WEIGHT × (len(my_moves) - len(their_moves))
    """
    base = evaluate_positional(state, CENTER_BONUS_H3, EDGE_BONUS_H3, ADVANCE_BONUS_PER_ROW_H3)

    # Movimentos do jogador atual já foram gerados em state.get_moves()
    my_moves = len(state.get_moves())

    # Gera movimentos do adversário (caro, mas altamente informativo)
    if state.turn == WHITE:
        their_moves = len(generate_moves(
            state.black_bb, state.white_bb, state.kings_bb, BLACK
        ))
    else:
        their_moves = len(generate_moves(
            state.white_bb, state.black_bb, state.kings_bb, WHITE
        ))

    mobility = my_moves - their_moves

    # Do ponto de vista do maximizador (brancas):
    # se é turno das brancas, my_moves = brancas, their_moves = pretas
    # score positivo => vantagem para brancas (correto)
    # se é turno das pretas, my_moves = pretas, their_moves = brancas
    # precisamos inverter o sinal
    if state.turn == BLACK:
        mobility = -mobility

    return base + MOBILITY_WEIGHT * mobility
