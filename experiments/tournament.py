"""
Torneio controlado para avaliação experimental dos agentes.

Executa partidas automáticas entre configurações de agentes e coleta métricas
para comparação:
  - Minimax puro vs Alpha-Beta
  - h1 vs h2 vs h3
  - Efeito das Tabelas de Transposição
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Callable
from datetime import datetime
import uuid

from game.state import GameState
from game.constants import WHITE, BLACK


# ── Resultado de partida ───────────────────────────────────────────────────────

@dataclass
class GameResult:
    winner:          int          # +1 brancas, -1 pretas, 0 empate
    moves:           int
    white_metrics:   list[dict]   # métricas por jogada das brancas
    black_metrics:   list[dict]   # métricas por jogada das pretas
    duration_s:      float
    white_pieces_final: int = 0
    black_pieces_final: int = 0


# ── Agente wrapper ─────────────────────────────────────────────────────────────

AgentFn = Callable[[GameState], tuple]   # state → (move, score, metrics)


# ── Execução de partida ────────────────────────────────────────────────────────

def play_game(
    white_agent: AgentFn,
    black_agent: AgentFn,
    max_moves:  int = 200,
    verbose:    bool = False,
) -> GameResult:
    """Executa uma partida completa entre dois agentes."""
    state          = GameState.initial()
    move_count     = 0
    white_metrics  = []
    black_metrics  = []
    t0             = time.perf_counter()

    while not state.is_terminal() and move_count < max_moves:
        agent = white_agent if state.turn == WHITE else black_agent
        move, score, metrics = agent(state)

        if state.turn == WHITE:
            white_metrics.append(metrics)
        else:
            black_metrics.append(metrics)

        if verbose:
            from game.constants import BIT_TO_ROWCOL
            rc1 = BIT_TO_ROWCOL[move.from_sq]
            rc2 = BIT_TO_ROWCOL[move.to_sq]
            player = 'W' if state.turn == WHITE else 'B'
            print(f'[{player}] {rc1}→{rc2}  score={score}  '
                  f'd={metrics.get("depth","?")}  n={metrics.get("nodes","?")}')

        state      = state.apply_move(move)
        move_count += 1

    elapsed = time.perf_counter() - t0
    winner  = state.utility()
    if winner > 0:
        winner = 1
    elif winner < 0:
        winner = -1

    return GameResult(
        winner              = winner,
        moves               = move_count,
        white_metrics       = white_metrics,
        black_metrics       = black_metrics,
        duration_s          = elapsed,
        white_pieces_final  = state.white_count,
        black_pieces_final  = state.black_count,
    )


# ── Torneio round-robin ────────────────────────────────────────────────────────

@dataclass
class TournamentResult:
    name_a:       str
    name_b:       str
    wins_a:       int = 0
    wins_b:       int = 0
    draws:        int = 0
    total_games:  int = 0
    all_results:  list[GameResult] = field(default_factory=list)

    @property
    def win_rate_a(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.wins_a / self.total_games

    @property
    def win_rate_b(self) -> float:
        if self.total_games == 0:
            return 0.0
        return self.wins_b / self.total_games

    def summary(self) -> str:
        return (
            f"{self.name_a} vs {self.name_b} — "
            f"{self.total_games} jogos: "
            f"A={self.wins_a} ({self.win_rate_a:.0%})  "
            f"B={self.wins_b} ({self.win_rate_b:.0%})  "
            f"Empates={self.draws}"
        )


def run_tournament(
    agent_a:     AgentFn,
    agent_b:     AgentFn,
    name_a:      str = 'Agente A',
    name_b:      str = 'Agente B',
    num_games:   int = 20,
    max_moves:   int = 200,
    verbose:     bool = False,
    progress:    bool = True,
    log_tournament: bool = False,
    logger = None,
) -> TournamentResult:
    """
    Executa `num_games` partidas entre agent_a e agent_b.
    Cada agente joga metade das partidas como brancas e metade como pretas
    para eliminar viés de primeiro jogador.
    
    Args:
        log_tournament: Se True, registra log detalhado do torneio
        logger: Instância de GameLogger (se None, usa a global)
    """
    from datetime import datetime
    import uuid
    
    if log_tournament:
        from experiments.logger import get_logger, TournamentLog, GameLog
        if logger is None:
            logger = get_logger()
    
    result = TournamentResult(name_a=name_a, name_b=name_b)
    tournament_start = time.perf_counter()
    tournament_games = []

    for i in range(num_games):
        # Alterna lados a cada partida
        if i % 2 == 0:
            white, black = agent_a, agent_b
            white_name, black_name = name_a, name_b
        else:
            white, black = agent_b, agent_a
            white_name, black_name = name_b, name_a

        if progress:
            print(f'\rPartida {i+1}/{num_games}...', end='', flush=True)

        gr = play_game(white, black, max_moves=max_moves, verbose=verbose)
        result.all_results.append(gr)
        result.total_games += 1

        # Mapeia vencedor para agente
        if gr.winner == 0:
            result.draws += 1
        else:
            # Se white=agent_a e winner=+1 → a ganhou como brancas
            # Se white=agent_b e winner=+1 → b ganhou como brancas
            a_is_white = (i % 2 == 0)
            if gr.winner == 1:
                if a_is_white:
                    result.wins_a += 1
                else:
                    result.wins_b += 1
            else:  # winner == -1
                if a_is_white:
                    result.wins_b += 1
                else:
                    result.wins_a += 1
        
        # Registra jogo no log do torneio
        if log_tournament:
            result_str = 'WHITE_WIN' if gr.winner > 0 else ('BLACK_WIN' if gr.winner < 0 else 'DRAW')
            white_avg_nodes = sum(m.get('nodes', 0) for m in gr.white_metrics) // len(gr.white_metrics) if gr.white_metrics else 0
            black_avg_nodes = sum(m.get('nodes', 0) for m in gr.black_metrics) // len(gr.black_metrics) if gr.black_metrics else 0
            white_avg_depth = sum(m.get('depth', 0) for m in gr.white_metrics) // len(gr.white_metrics) if gr.white_metrics else 0
            black_avg_depth = sum(m.get('depth', 0) for m in gr.black_metrics) // len(gr.black_metrics) if gr.black_metrics else 0
            white_avg_time = sum(m.get('time_s', 0) for m in gr.white_metrics) / len(gr.white_metrics) if gr.white_metrics else 0
            black_avg_time = sum(m.get('time_s', 0) for m in gr.black_metrics) / len(gr.black_metrics) if gr.black_metrics else 0
            
            game_log = GameLog(
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                game_id=str(uuid.uuid4())[:8],
                white_player=white_name,
                black_player=black_name,
                result=result_str,
                total_moves=gr.moves,
                white_pieces_final=gr.white_pieces_final,
                black_pieces_final=gr.black_pieces_final,
                total_time_s=gr.duration_s,
                avg_time_per_move_s=gr.duration_s / max(gr.moves, 1),
                white_avg_time_s=white_avg_time,
                black_avg_time_s=black_avg_time,
                white_avg_nodes=white_avg_nodes,
                black_avg_nodes=black_avg_nodes,
                white_avg_depth=white_avg_depth,
                black_avg_depth=black_avg_depth,
                moves=[],
                notes=f"Partida {i+1} de {num_games} do torneio"
            )
            tournament_games.append(game_log)

    if progress:
        print()  # newline
    
    # Salva torneio se solicitado
    if log_tournament:
        tournament_duration = time.perf_counter() - tournament_start
        tournament_log = TournamentLog(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            tournament_id=str(uuid.uuid4())[:8],
            player_a=name_a,
            player_b=name_b,
            total_games=num_games,
            wins_a=result.wins_a,
            wins_b=result.wins_b,
            draws=result.draws,
            duration_s=tournament_duration,
            games=tournament_games,
        )
        logger.save_tournament(tournament_log, format="both")

    return result


# ── Agregação de métricas ──────────────────────────────────────────────────────

def aggregate_metrics(results: list[GameResult]) -> dict:
    """Calcula estatísticas médias de um conjunto de partidas."""
    all_nodes   = []
    all_depths  = []
    all_times   = []
    all_cutoffs = []
    all_moves   = [r.moves for r in results]

    for gr in results:
        for m in gr.white_metrics + gr.black_metrics:
            if 'nodes'   in m: all_nodes.append(m['nodes'])
            if 'depth'   in m: all_depths.append(m['depth'])
            if 'time_s'  in m: all_times.append(m['time_s'])
            if 'cutoffs' in m: all_cutoffs.append(m['cutoffs'])

    def avg(lst): return sum(lst) / len(lst) if lst else 0.0

    return {
        'avg_nodes_per_move':  avg(all_nodes),
        'avg_depth':           avg(all_depths),
        'avg_time_per_move_s': avg(all_times),
        'avg_cutoffs':         avg(all_cutoffs),
        'avg_game_length':     avg(all_moves),
        'total_games':         len(results),
    }
