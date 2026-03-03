"""
Interface gráfica Pygame para o jogo de Damas Brasileiras.

Modos:
  - Humano vs IA
  - IA vs IA (com animação entre jogadas)

Controles:
  - Clique na peça para selecioná-la (destinos legais se iluminam).
  - Clique no destino para jogar.
  - Pressione 'Q' ou feche a janela para sair.
  - Pressione 'R' para reiniciar.
"""

from __future__ import annotations
import time
import threading
from typing import Optional

import pygame

from game.state import GameState
from game.moves import Move
from game.constants import WHITE, BLACK, BIT_TO_ROWCOL, ROWCOL_TO_BIT
from game.bitboard import test_bit, iter_bits


# ── Configurações visuais ─────────────────────────────────────────────────────

CELL_SIZE   = 80
BOARD_SIZE  = CELL_SIZE * 8
PANEL_WIDTH = 260
WIN_W       = BOARD_SIZE + PANEL_WIDTH
WIN_H       = BOARD_SIZE

# Cores
C_LIGHT        = (240, 217, 181)  # casa clara
C_DARK         = (181, 136,  99)  # casa escura
C_HIGHLIGHT    = ( 50, 200,  50)  # seleção
C_LEGAL_DOT    = (100, 200, 100)  # destino legal
C_LAST_MOVE    = (200, 200,  50)  # última jogada
C_WHITE_PIECE  = (255, 255, 255)
C_BLACK_PIECE  = ( 30,  30,  30)
C_KING_CROWN   = (255, 215,   0)
C_BG_PANEL     = ( 40,  40,  40)
C_TEXT         = (220, 220, 220)
C_TEXT_ALT     = (180, 180, 100)


# ── Helpers ────────────────────────────────────────────────────────────────────

def sq_to_pixel(sq: int) -> tuple[int, int]:
    """Centro em pixels da casa `sq`."""
    r, c = BIT_TO_ROWCOL[sq]
    x = c * CELL_SIZE + CELL_SIZE // 2
    y = r * CELL_SIZE + CELL_SIZE // 2
    return x, y


def pixel_to_sq(px: int, py: int) -> int | None:
    """Casa correspondente ao clique em (px, py), ou None se inválida."""
    col = px // CELL_SIZE
    row = py // CELL_SIZE
    if 0 <= row < 8 and 0 <= col < 8:
        return ROWCOL_TO_BIT.get((row, col))
    return None


# ── Renderização ───────────────────────────────────────────────────────────────

def draw_board(surface: pygame.Surface, state: GameState,
               selected: int | None, legal_dests: set[int],
               last_move: Move | None):
    """Desenha o tabuleiro, peças, highlights."""
    # Grid
    for row in range(8):
        for col in range(8):
            color = C_LIGHT if (row + col) % 2 == 0 else C_DARK
            pygame.draw.rect(surface, color,
                             (col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE))

    # Última jogada (highlight suave)
    if last_move is not None:
        for sq in [last_move.from_sq, last_move.to_sq]:
            r, c = BIT_TO_ROWCOL[sq]
            s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
            s.fill((*C_LAST_MOVE, 80))
            surface.blit(s, (c * CELL_SIZE, r * CELL_SIZE))

    # Casa selecionada
    if selected is not None:
        r, c = BIT_TO_ROWCOL[selected]
        s = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
        s.fill((*C_HIGHLIGHT, 120))
        surface.blit(s, (c * CELL_SIZE, r * CELL_SIZE))

    # Destinos legais
    for sq in legal_dests:
        x, y = sq_to_pixel(sq)
        pygame.draw.circle(surface, C_LEGAL_DOT, (x, y), CELL_SIZE // 6)

    # Peças
    for sq in iter_bits(state.white_bb):
        x, y = sq_to_pixel(sq)
        pygame.draw.circle(surface, C_WHITE_PIECE, (x, y), CELL_SIZE // 2 - 6)
        pygame.draw.circle(surface, (150, 150, 150), (x, y), CELL_SIZE // 2 - 6, 3)
        if test_bit(state.kings_bb, sq):
            _draw_crown(surface, x, y, C_KING_CROWN)

    for sq in iter_bits(state.black_bb):
        x, y = sq_to_pixel(sq)
        pygame.draw.circle(surface, C_BLACK_PIECE, (x, y), CELL_SIZE // 2 - 6)
        pygame.draw.circle(surface, (100, 100, 100), (x, y), CELL_SIZE // 2 - 6, 3)
        if test_bit(state.kings_bb, sq):
            _draw_crown(surface, x, y, C_KING_CROWN)

    # Coordenadas
    font_small = pygame.font.SysFont('monospace', 14)
    for sq in range(32):
        r, c = BIT_TO_ROWCOL[sq]
        label = font_small.render(f'{r},{c}', True, (80, 80, 80))
        surface.blit(label, (c * CELL_SIZE + 3, r * CELL_SIZE + 3))


def _draw_crown(surface: pygame.Surface, cx: int, cy: int, color):
    """Desenha uma pequena coroa no centro da peça."""
    r = CELL_SIZE // 6
    points = [
        (cx - r,     cy + r // 2),
        (cx - r // 2, cy - r // 2),
        (cx,          cy + r // 3),
        (cx + r // 2, cy - r // 2),
        (cx + r,      cy + r // 2),
    ]
    pygame.draw.polygon(surface, color, points)


def draw_panel(surface: pygame.Surface, state: GameState,
               metrics: dict, move_count: int, font):
    """Painel lateral com informações do jogo."""
    panel = pygame.Surface((PANEL_WIDTH, WIN_H))
    panel.fill(C_BG_PANEL)
    x = 10
    y = 10

    def text(msg, color=C_TEXT, small=False):
        nonlocal y
        f = pygame.font.SysFont('monospace', 14 if small else 18)
        surf = f.render(msg, True, color)
        panel.blit(surf, (x, y))
        y += surf.get_height() + 4

    text('DAMAS BRASILEIRAS', C_TEXT_ALT)
    text('')
    text(f"Turno: {'BRANCAS' if state.turn == WHITE else 'PRETAS'}")
    text(f'Jogada: {move_count}')
    text('')
    text('─── PEÇAS ───', C_TEXT_ALT)
    text(f'Brancas: {state.white_count} ({state.white_kings} damas)')
    text(f'Pretas:  {state.black_count} ({state.black_kings} damas)')
    text(f'Progresso: {state.no_progress}/20')
    text('')
    if metrics:
        text('─── IA STATS ───', C_TEXT_ALT)
        text(f"Profundidade: {metrics.get('depth','?')}", small=True)
        text(f"Nós: {metrics.get('nodes','?')}", small=True)
        text(f"Cutoffs: {metrics.get('cutoffs','?')}", small=True)
        text(f"TT hits: {metrics.get('tt_hits','?')}", small=True)
        text(f"Tempo: {metrics.get('time_s',0):.3f}s", small=True)
    text('')
    text('─── CONTROLES ───', C_TEXT_ALT)
    text('Q: sair', small=True)
    text('R: reiniciar', small=True)

    surface.blit(panel, (BOARD_SIZE, 0))


# ── Loop principal da GUI ──────────────────────────────────────────────────────

def play_gui(
    white_agent=None,   # None = humano; callable(state) → (move, score, metrics)
    black_agent=None,
    ai_delay: float = 0.3,
) -> int:
    """
    Executa o jogo com interface Pygame.

    Returns:
        +1 vitória branca, -1 vitória preta, 0 empate
    """
    pygame.init()
    pygame.display.set_caption('Damas Brasileiras – MC906')
    screen   = pygame.display.set_mode((WIN_W, WIN_H))
    clock    = pygame.time.Clock()
    font     = pygame.font.SysFont('monospace', 18)

    def reset():
        return GameState.initial(), None, set(), None, {}, 0, False

    state, selected, legal_dests, last_move, metrics, move_count, ai_thinking = reset()

    running = True

    while running:
        # ── Eventos ──────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_q, pygame.K_ESCAPE):
                    running = False
                elif event.key == pygame.K_r:
                    state, selected, legal_dests, last_move, metrics, move_count, ai_thinking = reset()

            elif event.type == pygame.MOUSEBUTTONDOWN and not ai_thinking:
                px, py = event.pos
                if px < BOARD_SIZE and not state.is_terminal():
                    agent = white_agent if state.turn == WHITE else black_agent
                    if agent is None:
                        # Clique do humano
                        clicked_sq = pixel_to_sq(px, py)
                        if clicked_sq is not None:
                            own = state.own_bb
                            if selected is None:
                                # Seleciona peça
                                if test_bit(own, clicked_sq):
                                    selected     = clicked_sq
                                    legal_moves  = state.get_moves()
                                    legal_dests  = {m.to_sq for m in legal_moves
                                                    if m.from_sq == clicked_sq}
                            else:
                                if clicked_sq in legal_dests:
                                    # Executa movimento
                                    moves = [m for m in state.get_moves()
                                             if m.from_sq == selected and m.to_sq == clicked_sq]
                                    if moves:
                                        move       = moves[0]
                                        state      = state.apply_move(move)
                                        last_move  = move
                                        move_count += 1
                                        metrics    = {}
                                selected    = None
                                legal_dests = set()

        # ── Jogada da IA ─────────────────────────────────────────────────────
        if not state.is_terminal() and not ai_thinking:
            agent = white_agent if state.turn == WHITE else black_agent
            if agent is not None:
                ai_thinking = True

                def _run_ai():
                    nonlocal state, last_move, metrics, move_count, ai_thinking, selected, legal_dests
                    time.sleep(ai_delay)
                    move, score, m = agent(state)
                    state      = state.apply_move(move)
                    last_move  = move
                    metrics    = m
                    move_count += 1
                    selected   = None
                    legal_dests = set()
                    ai_thinking = False

                t = threading.Thread(target=_run_ai, daemon=True)
                t.start()

        # ── Renderização ─────────────────────────────────────────────────────
        screen.fill(C_DARK)
        board_surface = pygame.Surface((BOARD_SIZE, BOARD_SIZE))
        draw_board(board_surface, state, selected, legal_dests, last_move)
        screen.blit(board_surface, (0, 0))
        draw_panel(screen, state, metrics, move_count, font)

        # Mensagem de fim de jogo
        if state.is_terminal():
            util = state.utility()
            if util > 0:
                msg = 'VITÓRIA DAS BRANCAS!'
            elif util < 0:
                msg = 'VITÓRIA DAS PRETAS!'
            else:
                msg = 'EMPATE!'
            f = pygame.font.SysFont('monospace', 36, bold=True)
            surf = f.render(msg, True, (255, 255, 0))
            screen.blit(surf, (BOARD_SIZE // 2 - surf.get_width() // 2,
                               BOARD_SIZE // 2 - surf.get_height() // 2))

        # "Thinking..."
        if ai_thinking:
            f = pygame.font.SysFont('monospace', 24, bold=True)
            surf = f.render('Pensando...', True, (255, 200, 50))
            screen.blit(surf, (10, BOARD_SIZE - 40))

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    return state.utility()
