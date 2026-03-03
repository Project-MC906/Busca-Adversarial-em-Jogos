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
    lines.append('    0   1   2   3   4   5   6   7')
    lines.append('  +---+---+---+---+---+---+---+---+')
    for r, row in enumerate(grid):
        cells = ' | '.join(row)
        lines.append(f'{r} | {cells} |')
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
    Converte 'r,c' ou 'rc' (ex: '3,2' ou '32') para índice de bit.
    Retorna None se inválido.
    """
    token = token.strip()
    if ',' in token:
        parts = token.split(',')
    elif len(token) == 2:
        parts = list(token)
    else:
        return None
    try:
        r, c = int(parts[0]), int(parts[1])
    except (ValueError, IndexError):
        return None
    return ROWCOL_TO_BIT.get((r, c))


def select_human_move(state: GameState) -> Move | None:
    """Interação com o usuário para selecionar um movimento."""
    legal = state.get_moves()
    if not legal:
        return None

    print('\nMovimentos legais:')
    for i, m in enumerate(legal):
        from_rc = BIT_TO_ROWCOL[m.from_sq]
        to_rc   = BIT_TO_ROWCOL[m.to_sq]
        caps    = f' (captura {len(m.captured)}x)' if m.is_capture else ''
        print(f'  [{i}] {from_rc} → {to_rc}{caps}')

    while True:
        raw = input('\nEscolha pelo índice ou "origemDestino" (ex: 5,0 -> 4,1): ').strip()

        # Seleção por índice
        try:
            idx = int(raw)
            if 0 <= idx < len(legal):
                return legal[idx]
        except ValueError:
            pass

        # Seleção por coordenadas "r1,c1 r2,c2"
        parts = raw.replace('->', ' ').replace('→', ' ').split()
        if len(parts) >= 2:
            from_sq = parse_sq(parts[0])
            to_sq   = parse_sq(parts[-1])
            if from_sq is not None and to_sq is not None:
                candidates = [m for m in legal if m.from_sq == from_sq and m.to_sq == to_sq]
                if len(candidates) == 1:
                    return candidates[0]
                if len(candidates) > 1:
                    print('Múltiplas rotas de captura possíveis:')
                    for i, m in enumerate(candidates):
                        print(f'  [{i}] {m}')
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
) -> int:
    """
    Executa uma partida no terminal.

    Args:
        white_agent: Agente para as brancas (None = humano)
        black_agent: Agente para as pretas  (None = humano)
        delay:       Pausa (s) entre jogadas IA vs IA para legibilidade
        verbose:     Exibe tabuleiro a cada jogada

    Returns:
        +1 vitória branca, -1 vitória preta, 0 empate
    """
    state = GameState.initial()
    move_count = 0

    while not state.is_terminal():
        if verbose:
            print('\n' + '='*50)
            print(render(state))

        agent = white_agent if state.turn == WHITE else black_agent

        if agent is None:
            # Humano
            move = select_human_move(state)
            if move is None:
                break
        else:
            t0 = time.perf_counter()
            move, score, metrics = agent(state)
            elapsed = time.perf_counter() - t0

            if verbose:
                from_rc = BIT_TO_ROWCOL[move.from_sq]
                to_rc   = BIT_TO_ROWCOL[move.to_sq]
                caps    = f' (captura {len(move.captured)}x)' if move.is_capture else ''
                player  = 'BRANCAS' if state.turn == WHITE else 'PRETAS'
                print(f'\n[IA {player}] {from_rc} → {to_rc}{caps}  '
                      f'score={score}  depth={metrics.get("depth","?")}  '
                      f'nodes={metrics.get("nodes","?")}  '
                      f'time={elapsed:.3f}s')

            if delay > 0:
                time.sleep(delay)

        state = state.apply_move(move)
        move_count += 1

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

    return state.utility()
