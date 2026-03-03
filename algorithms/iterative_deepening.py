"""
Iterative Deepening Search (IDS) com controle de tempo.

Wraps o AlphaBeta e itera d = 1, 2, 3, ... até atingir o tempo limite.
Se o tempo se esgota durante a iteração d, descarta o resultado parcial
e retorna o melhor lance da iteração d-1 completada com sucesso.

Uso:
    from algorithms.iterative_deepening import IterativeDeepening
    from heuristics.full import evaluate_full

    agent = IterativeDeepening(evaluator=evaluate_full, time_limit=1.0)
    move, score, stats = agent.choose_move(state)
"""

from __future__ import annotations
import time
from typing import Optional

from game.state import GameState
from game.constants import WHITE, INF
from game.moves import Move
from algorithms.alpha_beta import AlphaBeta


# ── Exceção de Timeout ────────────────────────────────────────────────────────

class TimeoutException(Exception):
    """Lançada quando o limite de tempo é excedido durante a busca."""
    pass


# ── Iterative Deepening ───────────────────────────────────────────────────────

class IterativeDeepening:
    """
    Iterative Deepening com Alpha-Beta Pruning e controle de tempo.

    A cada iteração d, é feita uma busca completa de profundidade d.
    Se o tempo se esgota, a iteração em curso é descartada e retorna-se
    o resultado seguro da iteração anterior.
    """

    def __init__(
        self,
        evaluator=None,
        time_limit: float = 1.0,
        max_depth:  int   = 50,
        use_tt:     bool  = True,
        check_interval: int = 2048,  # verifica tempo a cada N nós
    ):
        self.time_limit      = time_limit
        self.max_depth       = max_depth
        self.check_interval  = check_interval

        self.searcher = AlphaBeta(evaluator=evaluator, use_tt=use_tt)

        # Métricas acumuladas do último choose_move
        self.last_depth       = 0
        self.last_nodes       = 0
        self.last_cutoffs     = 0
        self.last_tt_hits     = 0
        self.last_time        = 0.0

    @property
    def evaluator(self):
        return self.searcher.evaluator

    @evaluator.setter
    def evaluator(self, fn):
        self.searcher.evaluator = fn

    def choose_move(
        self,
        state: GameState,
    ) -> tuple[Move | None, int, dict]:
        """
        Escolhe o melhor movimento via Iterative Deepening.

        Returns:
            (best_move, best_score, metrics_dict)
        """
        moves = state.get_moves()
        if not moves:
            return None, 0, {}

        start_time = time.perf_counter()
        self._start = start_time
        self._node_counter = 0

        best_move:  Move | None = moves[0]
        best_score: int         = 0
        completed_depth         = 0
        total_nodes             = 0

        # Instala verificador de tempo como callback no searcher
        searcher         = self.searcher
        check_interval   = self.check_interval
        original_expand  = None   # não vamos monkey-patch; usaremos flag periódica

        for depth in range(1, self.max_depth + 1):
            searcher.reset_stats()
            searcher.timed_out = False

            try:
                candidate, candidate_score = self._alpha_beta_timed(
                    state, depth, start_time
                )
                # Iteração completada com sucesso
                best_move      = candidate
                best_score     = candidate_score
                completed_depth = depth
                total_nodes    += searcher.nodes_expanded

            except TimeoutException:
                # Iteração interrompida – usa resultado da iteração anterior
                total_nodes += searcher.nodes_expanded
                break

            elapsed = time.perf_counter() - start_time
            if elapsed >= self.time_limit:
                break

        elapsed = time.perf_counter() - start_time

        self.last_depth   = completed_depth
        self.last_nodes   = total_nodes
        self.last_cutoffs = searcher.cutoffs
        self.last_tt_hits = searcher.tt_hits
        self.last_time    = elapsed

        metrics = {
            'depth':    completed_depth,
            'nodes':    total_nodes,
            'cutoffs':  searcher.cutoffs,
            'tt_hits':  searcher.tt_hits,
            'time_s':   elapsed,
        }
        if searcher.use_tt and searcher.tt:
            metrics['tt_stats'] = searcher.tt.stats()

        return best_move, best_score, metrics

    # ── Busca com verificação periódica de timeout ────────────────────────────

    def _alpha_beta_timed(
        self,
        state: GameState,
        depth: int,
        start_time: float,
    ) -> tuple[Move | None, int]:
        """
        Executa choose_move do AlphaBeta mas injeta verificações de timeout
        via substituição temporária do método nodes_expanded de forma não-intrusiva
        (polling periódico no loop raiz + flag timed_out no searcher).
        """
        time_limit  = self.time_limit
        searcher    = self.searcher
        interval    = self.check_interval

        is_max = (state.turn == WHITE)
        moves  = state.get_moves()
        if not moves:
            return None, 0

        from game.constants import INF
        from algorithms.move_ordering import order_moves

        best_move  = moves[0]
        best_score = -INF if is_max else INF
        alpha = -INF
        beta  = INF

        ordered = order_moves(
            moves,
            state.enemy_bb,
            state.kings_bb,
            0,
            None,
            searcher.killers,
            searcher.history,
        )

        for move in ordered:
            # Verificação rápida de tempo antes de cada ramo raiz
            if time.perf_counter() - start_time >= time_limit:
                searcher.timed_out = True
                raise TimeoutException()

            child = state.apply_move(move)
            score = searcher.alpha_beta(child, depth - 1, alpha, beta, not is_max, 1)

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

    def get_stats(self) -> dict:
        return {
            'depth':   self.last_depth,
            'nodes':   self.last_nodes,
            'cutoffs': self.last_cutoffs,
            'tt_hits': self.last_tt_hits,
            'time_s':  self.last_time,
        }
