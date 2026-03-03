"""
Interface de texto (terminal) para o jogo de Damas Brasileiras.

Permite:
  - Jogar como humano vs IA
  - Assistir partidas IA vs IA
  - Exibir métricas após cada jogada da IA
"""

from __future__ import annotations
import time

from game.state import GameState
from game.moves import Move
from game.constants import WHITE, BLACK, BIT_TO_ROWCOL, ROWCOL_TO_BIT
from game.chess_notation import rowcol_to_chess, chess_to_rowcol
from game.bitboard import test_bit, iter_bits


# ── Renderização ──────────────────────────────────────────────────────────────

def render(state: GameState, highlights: set[int] | None = None) -> str:
    """
    Retorna uma string representando o tabuleiro.

    Símbolos:
      w = pedra branca     W = dama branca
      b = pedra preta      B = dama preta
      * = casa destacada   . = casa escura vazia
        = casa clara
    """
    grid = [[' ' for _ in range(8)] for _ in range(8)]
    highlights = highlights or set()

    # Marca casas escuras vazias
    for sq in range(32):
        row, col = BIT_TO_ROWCOL[sq]
        if sq in highlights:
            grid[row][col] = '*'
        else:
            grid[row][col] = '.'

    # Peças
    for sq in iter_bits(state.white_bb):
        row, col = BIT_TO_ROWCOL[sq]
        grid[row][col] = 'W' if test_bit(state.kings_bb, sq) else 'w'

    for sq in iter_bits(state.black_bb):
        row, col = BIT_TO_ROWCOL[sq]
        grid[row][col] = 'B' if test_bit(state.kings_bb, sq) else 'b'

    lines = []
    lines.append('    a   b   c   d   e   f   g   h')
    lines.append('  +---+---+---+---+---+---+---+---+')
    for r, row in enumerate(grid):
        cells = ' | '.join(row)
        row_num = 8 - r
        lines.append(f'{row_num} | {cells} |')
        lines.append('  +---+---+---+---+---+---+---+---+')

    turn_str = 'BRANCAS (w/W)' if state.turn == WHITE else 'PRETAS (b/B)'
    lines.append(f'\nVez de: {turn_str}')
    lines.append(f'Peças B: {state.white_count} (damas: {state.white_kings})  '
                 f'Peças P: {state.black_count} (damas: {state.black_kings})')
    lines.append(f'Sem progresso: {state.no_progress}/20')
    return '\n'.join(lines)


# ── Parser de entrada humana ───────────────────────────────────────────────────

def parse_sq(token: str) -> int | None:
    """
    Converte notação de xadrez (ex: 'a8', 'h1') para índice de bit.
    Também aceita formato antigo 'r,c' (ex: '3,2') por compatibilidade.
    Retorna None se inválido.
    """
    token = token.strip().lower()
    
    # Tenta notação xadrez primeiro (ex: 'a8')
    if len(token) == 2 and token[0] in 'abcdefgh' and token[1] in '12345678':
        rc = chess_to_rowcol(token)
        if rc:
            r, c = rc
            return ROWCOL_TO_BIT.get((r, c))
    
    # Tenta formato antigo 'r,c'
    if ',' in token:
        parts = token.split(',')
        try:
            r, c = int(parts[0]), int(parts[1])
            return ROWCOL_TO_BIT.get((r, c))
        except (ValueError, IndexError):
            pass
    
    return None


def select_human_move(state: GameState) -> Move | None:
    """Interação com o usuário para selecionar um movimento."""
    legal = state.get_moves()
    if not legal:
        return None

    print('\nMovimentos legais:')
    for i, m in enumerate(legal):
        from_rc = BIT_TO_ROWCOL[m.from_sq]
        to_rc   = BIT_TO_ROWCOL[m.to_sq]
        from_chess = rowcol_to_chess(*from_rc)
        to_chess = rowcol_to_chess(*to_rc)
        caps    = f' (captura {len(m.captured)}x)' if m.is_capture else ''
        print(f'  [{i}] {from_chess}{to_chess}{caps}')

    while True:
        raw = input('\nEscolha pelo índice ou "origemDestino" (ex: 5,0 -> 4,1): ').strip()

        # Seleção por índice
        try:
            idx = int(raw)
            if 0 <= idx < len(legal):
                return legal[idx]
        except ValueError:
            pass

        # Seleção por coordenadas de xadrez "a8h1" ou notação alternativa
        parts = raw.replace('->', ' ').replace('→', ' ').replace(' ', '').split()
        if len(parts) == 0:
            print('Entrada inválida. Tente novamente.')
            continue
            
        raw_clean = parts[0].lower()
        if len(raw_clean) == 4 and raw_clean[0] in 'abcdefgh' and raw_clean[2] in 'abcdefgh':
            from_sq = parse_sq(raw_clean[0:2])
            to_sq = parse_sq(raw_clean[2:4])
            if from_sq is not None and to_sq is not None:
                candidates = [m for m in legal if m.from_sq == from_sq and m.to_sq == to_sq]
                if len(candidates) == 1:
                    return candidates[0]
                if len(candidates) > 1:
                    print('Múltiplas rotas de captura possíveis:')
                    for i, m in enumerate(candidates):
                        from_rc = BIT_TO_ROWCOL[m.from_sq]
                        to_rc   = BIT_TO_ROWCOL[m.to_sq]
                        from_chess = rowcol_to_chess(*from_rc)
                        to_chess = rowcol_to_chess(*to_rc)
                        caps    = f' (captura {len(m.captured)}x)' if m.is_capture else ''
                        print(f'  [{i}] {from_chess}{to_chess}{caps}')
                    try:
                        idx = int(input('Índice: '))
                        if 0 <= idx < len(candidates):
                            return candidates[idx]
                    except ValueError:
                        pass

        print('Entrada inválida. Tente novamente.')


# ── Loop principal de jogo ─────────────────────────────────────────────────────

def play_terminal(
    white_agent=None,   # None = humano; callable(state) → (move, score, metrics)
    black_agent=None,
    delay: float = 0.0,
    verbose: bool = True,
    white_name: str = "Humano",
    black_name: str = "Humano",
    log_game: bool = False,
    logger = None,
) -> tuple[int, dict] | int:
    """
    Executa uma partida no terminal com logging opcional.

    Args:
        white_agent: Agente para as brancas (None = humano)
        black_agent: Agente para as pretas  (None = humano)
        delay:       Pausa (s) entre jogadas IA vs IA para legibilidade
        verbose:     Exibe tabuleiro a cada jogada
        white_name:  Nome/identificação do agente branco
        black_name:  Nome/identificação do agente preto
        log_game:    Se True, registra log detalhado do jogo
        logger:      Instância de GameLogger (se None, usa a global)

    Returns:
        Se log_game=False: +1 vitória branca, -1 vitória preta, 0 empate
        Se log_game=True: (resultado, dict com dados do jogo)
    """
    from datetime import datetime
    import uuid

    if log_game:
        from experiments.logger import get_logger, GameLog, MoveLog
        if logger is None:
            logger = get_logger()

    state = GameState.initial()
    move_count = 0
    total_time = 0.0
    move_logs = []
    white_times = []
    black_times = []
    white_nodes = []
    black_nodes = []
    white_depths = []
    black_depths = []

    game_start = time.perf_counter()

    while not state.is_terminal():
        if verbose:
            print('\n' + '='*50)
            print(render(state))

        agent = white_agent if state.turn == WHITE else black_agent
        is_white = state.turn == WHITE

        if agent is None:
            # Humano
            move = select_human_move(state)
            if move is None:
                break
            move_time = 0.0
            metrics = {}
        else:
            t0 = time.perf_counter()
            move, score, metrics = agent(state)
            move_time = time.perf_counter() - t0
            total_time += move_time

            if is_white:
                white_times.append(move_time)
                white_nodes.append(metrics.get("nodes", 0))
                white_depths.append(metrics.get("depth", 0))
            else:
                black_times.append(move_time)
                black_nodes.append(metrics.get("nodes", 0))
                black_depths.append(metrics.get("depth", 0))

            if verbose:
                from_rc = BIT_TO_ROWCOL[move.from_sq]
                to_rc   = BIT_TO_ROWCOL[move.to_sq]
                from_chess = rowcol_to_chess(*from_rc)
                to_chess = rowcol_to_chess(*to_rc)
                caps    = f' (captura {len(move.captured)}x)' if move.is_capture else ''
                player  = 'BRANCAS' if is_white else 'PRETAS'
                print(f'\n[IA {player}] {from_chess}{to_chess}{caps}  '
                      f'score={metrics.get("score", "?")}  depth={metrics.get("depth","?")}  '
                      f'nodes={metrics.get("nodes","?")}  '
                      f'time={move_time:.3f}s')

            if delay > 0:
                time.sleep(delay)

        # Registra movimento se logging ativo
        if log_game:
            from_rc = BIT_TO_ROWCOL[move.from_sq]
            to_rc   = BIT_TO_ROWCOL[move.to_sq]
            from_chess = rowcol_to_chess(*from_rc)
            to_chess = rowcol_to_chess(*to_rc)
            move_notation = f"{from_chess}{to_chess}"
            move_log = MoveLog(
                move_number=move_count + 1,
                player="WHITE" if is_white else "BLACK",
                move_notation=move_notation,
                time_s=move_time,
                nodes_expanded=metrics.get("nodes", 0),
                depth_reached=metrics.get("depth", 0),
                score=metrics.get("score", 0),
                white_pieces=state.white_count,
                black_pieces=state.black_count,
            )
            move_logs.append(move_log)

        state = state.apply_move(move)
        move_count += 1

    game_duration = time.perf_counter() - game_start

    if verbose:
        print('\n' + '='*50)
        print(render(state))
        util = state.utility()
        if util > 0:
            print('\n🏆 VITÓRIA DAS BRANCAS!')
        elif util < 0:
            print('\n🏆 VITÓRIA DAS PRETAS!')
        else:
            print('\n🤝 EMPATE!')
        print(f'Total de jogadas: {move_count}')

    result = state.utility()

    # Salva log se solicitado
    if log_game:
        result_str = 'WHITE_WIN' if result > 0 else ('BLACK_WIN' if result < 0 else 'DRAW')
        avg_time = game_duration / max(move_count, 1)
        white_avg_time = sum(white_times) / len(white_times) if white_times else 0.0
        black_avg_time = sum(black_times) / len(black_times) if black_times else 0.0
        white_avg_nodes = sum(white_nodes) // len(white_nodes) if white_nodes else 0
        black_avg_nodes = sum(black_nodes) // len(black_nodes) if black_nodes else 0
        white_avg_depth = sum(white_depths) // len(white_depths) if white_depths else 0
        black_avg_depth = sum(black_depths) // len(black_depths) if black_depths else 0

        game_log = GameLog(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            game_id=str(uuid.uuid4())[:8],
            white_player=white_name,
            black_player=black_name,
            result=result_str,
            total_moves=move_count,
            white_pieces_final=state.white_count,
            black_pieces_final=state.black_count,
            total_time_s=game_duration,
            avg_time_per_move_s=avg_time,
            white_avg_time_s=white_avg_time,
            black_avg_time_s=black_avg_time,
            white_avg_nodes=white_avg_nodes,
            black_avg_nodes=black_avg_nodes,
            white_avg_depth=white_avg_depth,
            black_avg_depth=black_avg_depth,
            moves=move_logs,
        )
        logger.save_game(game_log, format="both")
        if verbose:
            print(f'\n📝 Log salvo')
        return result, game_log.to_dict()

    return result
