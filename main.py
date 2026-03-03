"""
Damas Brasileiras — Agente de Busca Adversarial
MC906 – Unicamp

Uso:
  python main.py play --mode human_vs_ai [--heuristic h1|h2|h3] [--time 1.0] [--gui]
  python main.py play --mode ai_vs_ai    [--white h1|h2|h3] [--black h1|h2|h3] [--gui]
  python main.py tournament [--games 20] [--time 1.0]
  python main.py experiments [--games 10] [--time 1.0]
  python main.py demo        (IA vs IA na GUI, h3 vs h2)
"""

import argparse
import sys


# ── Helpers para criar agentes ────────────────────────────────────────────────

def _get_evaluator(name: str):
    from heuristics.material   import evaluate_material
    from heuristics.positional import evaluate_positional
    from heuristics.full       import evaluate_full
    mapping = {'h1': evaluate_material, 'h2': evaluate_positional, 'h3': evaluate_full}
    if name not in mapping:
        print(f'Heurística desconhecida: {name}. Use h1, h2 ou h3.')
        sys.exit(1)
    return mapping[name]


def _make_agent(heuristic: str = 'h3', time_limit: float = 1.0, use_tt: bool = True):
    from algorithms.iterative_deepening import IterativeDeepening
    evaluator = _get_evaluator(heuristic)
    engine    = IterativeDeepening(evaluator=evaluator, time_limit=time_limit, use_tt=use_tt)
    def agent(state):
        return engine.choose_move(state)
    return agent


# ── Subcomandos ───────────────────────────────────────────────────────────────

def cmd_play(args):
    mode       = args.mode
    time_limit = args.time
    use_gui    = getattr(args, 'gui', False)

    if mode == 'human_vs_ai':
        heuristic = getattr(args, 'heuristic', 'h3')
        ia = _make_agent(heuristic, time_limit)
        white_agent = None   # humano
        black_agent = ia
        print(f'Modo: Humano (Brancas) vs IA-{heuristic} (Pretas) | tempo={time_limit}s')

    elif mode == 'ai_vs_ia':
        mode = 'ai_vs_ai'  # normaliza
        white_h = getattr(args, 'white', 'h3')
        black_h = getattr(args, 'black', 'h2')
        white_agent = _make_agent(white_h, time_limit)
        black_agent = _make_agent(black_h, time_limit)
        print(f'Modo: IA-{white_h} (Brancas) vs IA-{black_h} (Pretas) | tempo={time_limit}s')

    elif mode == 'ai_vs_ai':
        white_h = getattr(args, 'white', 'h3')
        black_h = getattr(args, 'black', 'h2')
        white_agent = _make_agent(white_h, time_limit)
        black_agent = _make_agent(black_h, time_limit)
        print(f'Modo: IA-{white_h} (Brancas) vs IA-{black_h} (Pretas) | tempo={time_limit}s')

    else:
        print(f'Modo desconhecido: {mode}')
        sys.exit(1)

    if use_gui:
        from ui.gui import play_gui
        result = play_gui(white_agent=white_agent, black_agent=black_agent)
    else:
        from ui.terminal import play_terminal
        result = play_terminal(white_agent=white_agent, black_agent=black_agent)

    if result > 0:
        print('Resultado: Vitória das Brancas')
    elif result < 0:
        print('Resultado: Vitória das Pretas')
    else:
        print('Resultado: Empate')


def cmd_tournament(args):
    from experiments.tournament import run_tournament, aggregate_metrics
    from experiments.analysis   import make_id_agent
    from heuristics.material    import evaluate_material
    from heuristics.positional  import evaluate_positional
    from heuristics.full        import evaluate_full

    num_games  = args.games
    time_limit = args.time

    print(f'\nTorneio interno: {num_games} jogos por confronto | tempo={time_limit}s\n')

    agents = {
        'h1': make_id_agent(evaluate_material,   time_limit),
        'h2': make_id_agent(evaluate_positional, time_limit),
        'h3': make_id_agent(evaluate_full,       time_limit),
    }
    names = list(agents.keys())

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            na, nb = names[i], names[j]
            res = run_tournament(
                agents[na], agents[nb],
                name_a=na, name_b=nb,
                num_games=num_games,
                progress=True,
            )
            print(res.summary())
            agg = aggregate_metrics(res.all_results)
            print(f'  Profundidade média: {agg["avg_depth"]:.1f} | '
                  f'Nós/mov: {agg["avg_nodes_per_move"]:.0f} | '
                  f'Tempo/mov: {agg["avg_time_per_move_s"]:.3f}s\n')


def cmd_experiments(args):
    from experiments.analysis import run_all_experiments
    run_all_experiments(num_games=args.games, time_limit=args.time)


def cmd_demo(args):
    """Demonstração rápida: IA vs IA na GUI com h3 vs h2."""
    from experiments.analysis import make_id_agent
    from heuristics.full       import evaluate_full
    from heuristics.positional import evaluate_positional
    from ui.gui import play_gui

    white = make_id_agent(evaluate_full,       time_limit=1.0)
    black = make_id_agent(evaluate_positional, time_limit=1.0)
    play_gui(white_agent=white, black_agent=black, ai_delay=0.5)


# ── CLI ───────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description='Damas Brasileiras — MC906 Unicamp'
    )
    sub = parser.add_subparsers(dest='command')

    # play
    p_play = sub.add_parser('play', help='Jogar uma partida')
    p_play.add_argument('--mode', choices=['human_vs_ai', 'ai_vs_ai'],
                        default='human_vs_ai')
    p_play.add_argument('--heuristic', choices=['h1', 'h2', 'h3'], default='h3',
                        help='Heurística da IA (modo human_vs_ai)')
    p_play.add_argument('--white', choices=['h1', 'h2', 'h3'], default='h3',
                        help='Heurística das Brancas (modo ai_vs_ai)')
    p_play.add_argument('--black', choices=['h1', 'h2', 'h3'], default='h2',
                        help='Heurística das Pretas (modo ai_vs_ai)')
    p_play.add_argument('--time', type=float, default=1.0,
                        help='Limite de tempo por jogada (segundos)')
    p_play.add_argument('--gui', action='store_true',
                        help='Usar interface gráfica Pygame')

    # tournament
    p_tour = sub.add_parser('tournament', help='Torneio interno round-robin')
    p_tour.add_argument('--games', type=int, default=20,
                        help='Número de jogos por confronto')
    p_tour.add_argument('--time', type=float, default=1.0)

    # experiments
    p_exp = sub.add_parser('experiments', help='Todos os experimentos analíticos')
    p_exp.add_argument('--games', type=int, default=10)
    p_exp.add_argument('--time', type=float, default=1.0)

    # demo
    sub.add_parser('demo', help='IA vs IA na interface gráfica (demonstração)')

    return parser


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.command == 'play':
        cmd_play(args)
    elif args.command == 'tournament':
        cmd_tournament(args)
    elif args.command == 'experiments':
        cmd_experiments(args)
    elif args.command == 'demo':
        cmd_demo(args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
