"""
Análise experimental e geração de gráficos/tabelas para o relatório.

Experimentos:
  1. Minimax puro vs Alpha-Beta: nós expandidos e profundidade por depth fixa.
  2. Round-robin de heurísticas: h1 vs h2 vs h3.
  3. Impacto das Tabelas de Transposição.
  4. Curva de profundidade vs tempo (Iterative Deepening).
"""

from __future__ import annotations
import time

from experiments.tournament import run_tournament, play_game, aggregate_metrics
from algorithms.minimax           import Minimax
from algorithms.alpha_beta        import AlphaBeta
from algorithms.iterative_deepening import IterativeDeepening
from heuristics.connectivity import evaluate_connectivity
from heuristics.connectivity import evaluate_connectivity
from heuristics.material           import evaluate_material
from heuristics.positional         import evaluate_positional
from heuristics.full               import evaluate_full
from game.state import GameState
from game.constants import WHITE


# ── Wrappers de agente (chamáveis) ────────────────────────────────────────────

def make_minimax_agent(depth: int, evaluator=evaluate_material):
    """Cria um agente Minimax puro de profundidade fixa."""
    engine = Minimax(evaluator=evaluator)
    def agent(state: GameState):
        move, score = engine.choose_move(state, depth)
        stats = engine.get_stats()
        metrics = {
            'nodes':  stats['nodes_expanded'],
            'depth':  depth,
            'time_s': 0.0,
        }
        return move, score, metrics
    return agent


def make_alpha_beta_agent(depth: int, evaluator=evaluate_material, use_tt: bool = True):
    """Cria um agente Alpha-Beta de profundidade fixa."""
    engine = AlphaBeta(evaluator=evaluator, use_tt=use_tt)
    def agent(state: GameState):
        t0 = time.perf_counter()
        move, score = engine.choose_move(state, depth)
        elapsed = time.perf_counter() - t0
        stats = engine.get_stats()
        metrics = {
            'nodes':   stats['nodes_expanded'],
            'depth':   depth,
            'cutoffs': stats['cutoffs'],
            'tt_hits': stats.get('tt_hits', 0),
            'time_s':  elapsed,
        }
        return move, score, metrics
    return agent


def make_id_agent(evaluator=evaluate_full, time_limit: float = 1.0, use_tt: bool = True):
    """Cria um agente de Iterative Deepening (padrão do torneio)."""
    engine = IterativeDeepening(evaluator=evaluator, time_limit=time_limit, use_tt=use_tt)
    def agent(state: GameState):
        move, score, metrics = engine.choose_move(state)
        return move, score, metrics
    return agent


# ── Experimento 1: Minimax vs Alpha-Beta (nós por profundidade) ───────────────

def exp1_minimax_vs_alphabeta(depths=(1, 2, 3, 4, 5), num_positions: int = 5):
    """
    Para cada profundidade d, joga `num_positions` jogadas do estado inicial
    e compara nós expandidos entre Minimax e Alpha-Beta.
    """
    print('\n=== Experimento 1: Minimax vs Alpha-Beta ===')
    print(f"{'Depth':>6} | {'Minimax nós':>12} | {'AB nós':>10} | {'Redução':>8}")
    print('-' * 48)

    state = GameState.initial()
    for d in depths:
        mm  = Minimax(evaluator=evaluate_material)
        ab  = AlphaBeta(evaluator=evaluate_material, use_tt=False)

        mm.choose_move(state, d)
        ab.choose_move(state, d)

        mm_nodes = mm.nodes_expanded
        ab_nodes = ab.nodes_expanded
        ratio    = mm_nodes / ab_nodes if ab_nodes else float('inf')

        print(f"{d:>6} | {mm_nodes:>12,} | {ab_nodes:>10,} | {ratio:>7.1f}x")

    print()


# ── Experimento 2: Round-robin de heurísticas ─────────────────────────────────

def exp2_heuristic_tournament(num_games: int = 20, time_limit: float = 1.0, log_results: bool = False, logger = None):
    """Round-robin entre h1, h2, h3 usando Iterative Deepening."""
    print('\n=== Experimento 2: Torneio de Heurísticas ===')

    agents = {
        'h1-Material':   make_id_agent(evaluate_material,   time_limit),
        'h2-Posicional': make_id_agent(evaluate_positional, time_limit),
        'h3-Completa':   make_id_agent(evaluate_full,       time_limit),
        'h4-Conectividade': make_id_agent(evaluate_connectivity, time_limit),
    }
    names  = list(agents.keys())

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            na, nb = names[i], names[j]
            res = run_tournament(
                agents[na], agents[nb],
                name_a=na, name_b=nb,
                num_games=num_games,
                progress=True,
                log_tournament=log_results,
                logger=logger,
            )
            print(res.summary())
            agg = aggregate_metrics(res.all_results)
            print(f'  Profundidade média: {agg["avg_depth"]:.1f}  '
                  f'Nós/mov: {agg["avg_nodes_per_move"]:.0f}  '
                  f'Tempo/mov: {agg["avg_time_per_move_s"]:.3f}s')
    print()


# ── Experimento 3: Impacto da Tabela de Transposição ─────────────────────────

def exp3_tt_impact(depth: int = 4, num_games: int = 10, time_limit: float = 1.0, log_results: bool = False, logger = None):
    """Compara AB com TT vs AB sem TT."""
    print('\n=== Experimento 3: Impacto da TT ===')

    ab_tt    = make_id_agent(evaluate_full, time_limit, use_tt=True)
    ab_no_tt = make_id_agent(evaluate_full, time_limit, use_tt=False)

    res = run_tournament(
        ab_tt, ab_no_tt,
        name_a='AB+TT', name_b='AB-TT',
        num_games=num_games,
        progress=True,
        log_tournament=log_results,
        logger=logger,
    )
    print(res.summary())
    agg_a = aggregate_metrics([gr for gr in res.all_results])
    print(f'  Profundidade média: {agg_a["avg_depth"]:.1f}')
    print()


# ── Experimento 4: Win rate vs baseline aleatório ─────────────────────────────

def exp4_vs_random(num_games: int = 20, time_limit: float = 1.0):
    """Testa o agente contra um baseline aleatório."""
    import random

    def random_agent(state: GameState):
        moves = state.get_moves()
        move  = random.choice(moves) if moves else None
        return move, 0, {'nodes': 1, 'depth': 0, 'time_s': 0.0}

    print('\n=== Experimento 4: IA vs Aleatório ===')

    for name, evaluator in [('h1', evaluate_material),
                             ('h2', evaluate_positional),
                             ('h3', evaluate_full)]:
        agent = make_id_agent(evaluator, time_limit)
        res   = run_tournament(
            agent, random_agent,
            name_a=f'ID-{name}', name_b='Random',
            num_games=num_games,
            progress=True,
        )
        print(res.summary())
    print()


# ── Gráficos ──────────────────────────────────────────────────────────────────

def plot_nodes_comparison(depths=(1, 2, 3, 4, 5, 6)):
    """Plota nós expandidos: Minimax vs Alpha-Beta por profundidade."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print('matplotlib não disponível — pulando gráfico.')
        return

    state     = GameState.initial()
    mm_nodes  = []
    ab_nodes  = []

    for d in depths:
        mm = Minimax(evaluator=evaluate_material)
        ab = AlphaBeta(evaluator=evaluate_material, use_tt=False)
        mm.choose_move(state, d)
        ab.choose_move(state, d)
        mm_nodes.append(mm.nodes_expanded)
        ab_nodes.append(ab.nodes_expanded)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogy(depths, mm_nodes, 'o-', label='Minimax')
    ax.semilogy(depths, ab_nodes, 's-', label='Alpha-Beta')
    ax.set_xlabel('Profundidade')
    ax.set_ylabel('Nós expandidos (escala log)')
    ax.set_title('Minimax vs Alpha-Beta: nós expandidos')
    ax.legend()
    ax.grid(True, which='both', alpha=0.3)
    plt.tight_layout()
    plt.savefig('nodes_comparison.png', dpi=150)
    print('Gráfico salvo: nodes_comparison.png')
    plt.show()


# ── Entry point ────────────────────────────────────────────────────────────────

def run_all_experiments(num_games: int = 10, time_limit: float = 1.0, log_results: bool = False, logger = None):
    """Executa todos os experimentos em sequência.
    
    Args:
        log_results: Se True, registra logs dos torneios dos experimentos
        logger: Instância de GameLogger (se None, usa a global)
    """
    print('Iniciando experimentos... (pode levar vários minutos)')
    exp1_minimax_vs_alphabeta()
    exp2_heuristic_tournament(num_games=num_games, time_limit=time_limit, log_results=log_results, logger=logger)
    exp3_tt_impact(num_games=num_games, time_limit=time_limit, log_results=log_results, logger=logger)
    exp4_vs_random(num_games=num_games, time_limit=time_limit)
    plot_nodes_comparison()
    print('Experimentos concluídos.')
