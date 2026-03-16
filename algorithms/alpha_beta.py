"""
Alpha-Beta Pruning com:
  - Move Ordering (hash move, capturas, killer moves, history heuristic)
  - Tabela de Transposição (Zobrist Hashing)
  - Instrumentação (nós expandidos, cutoffs, profundidade)
"""

from __future__ import annotations
import time

from game.state import GameState
from game.constants import WHITE, INF
from game.moves import Move
from algorithms.transposition import (
    TranspositionTable, compute_hash,
    EXACT, LOWER_BOUND, UPPER_BOUND,
)
from algorithms.move_ordering import KillerMoves, HistoryTable, order_moves


class AlphaBeta:
    """Alpha-Beta Pruning com move ordering, TT e instrumentação."""

    def __init__(self, evaluator=None, use_tt: bool = True, check_interval: int = 512):
        self.evaluator      = evaluator
        self.use_tt         = use_tt
        self.tt             = TranspositionTable() if use_tt else None
        self.killers        = KillerMoves()
        self.history        = HistoryTable()
        self.nodes_expanded = 0
        self.cutoffs        = 0
        self.tt_hits        = 0
        self.depth_reached  = 0
        self.timed_out      = False
        self.check_interval = check_interval
        self._time_limit    = None   # definido pelo IterativeDeepening
        self._start_time    = None   # definido pelo IterativeDeepening

    def reset_stats(self):
        self.nodes_expanded = 0
        self.cutoffs        = 0
        self.tt_hits        = 0
        self.depth_reached  = 0
        self.timed_out      = False
        self.killers.clear()
        self.history.clear()

    def alpha_beta(self, state, depth, alpha, beta, is_maximizing, current_depth=0):
        from algorithms.iterative_deepening import TimeoutException
        if self.timed_out:
            raise TimeoutException()

        self.nodes_expanded += 1

        # Verifica timeout periodicamente sem chamar perf_counter a cada nó
        if (
            self._time_limit is not None
            and self.nodes_expanded % self.check_interval == 0
            and time.perf_counter() - self._start_time >= self._time_limit
        ):
            self.timed_out = True
            raise TimeoutException()
        if current_depth > self.depth_reached:
            self.depth_reached = current_depth

        z_key = None
        hash_move = None
        if self.use_tt and self.tt is not None:
            z_key = compute_hash(state)
            tt_score, hash_move = self.tt.lookup(z_key, depth, alpha, beta)
            if tt_score is not None:
                self.tt_hits += 1
                return tt_score

        if state.is_terminal():
            return state.utility()

        if depth == 0:
            return self.evaluator(state)

        moves = state.get_moves()
        ordered = order_moves(
            moves, state.enemy_bb, state.kings_bb,
            current_depth, hash_move, self.killers, self.history,
        )

        best_move = None

        if is_maximizing:
            best_score = -INF
            orig_alpha = alpha
            for move in ordered:
                child = state.apply_move(move)
                score = self.alpha_beta(child, depth-1, alpha, beta, False, current_depth+1)
                if score > best_score:
                    best_score = score
                    best_move  = move
                alpha = max(alpha, score)
                if beta <= alpha:
                    self.cutoffs += 1
                    if not move.is_capture:
                        self.killers.store(move, current_depth)
                        self.history.update(move, depth)
                    break
            if self.use_tt and self.tt is not None and z_key is not None:
                flag = EXACT if orig_alpha < best_score < beta else (
                    LOWER_BOUND if best_score >= beta else UPPER_BOUND)
                self.tt.store(z_key, best_score, flag, depth, best_move)
            return best_score
        else:
            best_score = INF
            orig_beta  = beta
            for move in ordered:
                child = state.apply_move(move)
                score = self.alpha_beta(child, depth-1, alpha, beta, True, current_depth+1)
                if score < best_score:
                    best_score = score
                    best_move  = move
                beta = min(beta, score)
                if beta <= alpha:
                    self.cutoffs += 1
                    if not move.is_capture:
                        self.killers.store(move, current_depth)
                        self.history.update(move, depth)
                    break
            if self.use_tt and self.tt is not None and z_key is not None:
                flag = EXACT if alpha < best_score < orig_beta else (
                    UPPER_BOUND if best_score <= alpha else LOWER_BOUND)
                self.tt.store(z_key, best_score, flag, depth, best_move)
            return best_score

    def choose_move(self, state, depth):
        self.reset_stats()
        moves = state.get_moves()
        if not moves:
            return None, 0

        is_max     = (state.turn == WHITE)
        best_move  = moves[0]
        best_score = -INF if is_max else INF
        alpha = -INF
        beta  = INF

        ordered = order_moves(
            moves, state.enemy_bb, state.kings_bb,
            0, None, self.killers, self.history,
        )

        for move in ordered:
            child = state.apply_move(move)
            score = self.alpha_beta(child, depth-1, alpha, beta, not is_max, 1)
            if is_max:
                if score > best_score:
                    best_score = score
                    best_move  = move
                alpha = max(alpha, score)
            else:
                if score < best_score:
                    best_score = score
                    best_move  = move
                beta = min(beta, score)

        return best_move, best_score

    def get_stats(self):
        stats = {
            'nodes_expanded': self.nodes_expanded,
            'cutoffs':        self.cutoffs,
            'depth_reached':  self.depth_reached,
            'tt_hits':        self.tt_hits,
        }
        if self.use_tt and self.tt:
            stats['tt_stats'] = self.tt.stats()
        return stats
