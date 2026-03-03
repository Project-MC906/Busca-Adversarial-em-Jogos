"""
Minimax puro (sem poda) — usado como baseline experimental.

Instrumentado para contagem de nós expandidos.
"""

from __future__ import annotations

from game.state import GameState
from game.constants import WHITE, INF
from game.moves import Move


class Minimax:
    """
    Minimax recursivo sem poda Alpha-Beta.
    Serve como baseline para comparação experimental com o Alpha-Beta.
    """

    def __init__(self, evaluator=None):
        self.evaluator      = evaluator
        self.nodes_expanded = 0
        self.depth_reached  = 0

    def reset_stats(self):
        self.nodes_expanded = 0
        self.depth_reached  = 0

    def minimax(
        self,
        state: GameState,
        depth: int,
        is_maximizing: bool,
        current_depth: int = 0,
    ) -> int:
        """
        Minimax recursivo.

        Returns:
            Valor heurístico/terminal da posição.
        """
        self.nodes_expanded += 1
        if current_depth > self.depth_reached:
            self.depth_reached = current_depth

        if state.is_terminal():
            return state.utility()

        if depth == 0:
            return self.evaluator(state)

        moves = state.get_moves()

        if is_maximizing:
            best = -INF
            for move in moves:
                child = state.apply_move(move)
                val   = self.minimax(child, depth - 1, False, current_depth + 1)
                best  = max(best, val)
            return best
        else:
            best = INF
            for move in moves:
                child = state.apply_move(move)
                val   = self.minimax(child, depth - 1, True, current_depth + 1)
                best  = min(best, val)
            return best

    def choose_move(
        self,
        state: GameState,
        depth: int,
    ) -> tuple[Move | None, int]:
        """
        Escolhe o melhor movimento no Minimax completo.

        Returns:
            (best_move, best_score)
        """
        self.reset_stats()
        moves = state.get_moves()
        if not moves:
            return None, 0

        is_max     = (state.turn == WHITE)
        best_move  = moves[0]
        best_score = -INF if is_max else INF

        for move in moves:
            child = state.apply_move(move)
            score = self.minimax(child, depth - 1, not is_max, 1)

            if is_max:
                if score > best_score:
                    best_score = score
                    best_move  = move
            else:
                if score < best_score:
                    best_score = score
                    best_move  = move

        return best_move, best_score

    def get_stats(self) -> dict:
        return {
            'nodes_expanded': self.nodes_expanded,
            'depth_reached':  self.depth_reached,
        }
