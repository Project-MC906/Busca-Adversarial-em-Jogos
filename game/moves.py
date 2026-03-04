"""
Geração de movimentos legais para Damas Brasileiras.

Regras implementadas:
- Captura obrigatória (se existir qualquer captura, movimentos simples são ilegais).
- Lei da Maioria: dentre todas as capturas possíveis, apenas as de máxima
  quantidade de peças capturadas são válidas.
- Damas voadoras: damas se movem e capturam ao longo de diagonais inteiras.
- Promoção durante um encadeamento de capturas NÃO ocorre (só ao finalizar o turno
  na fileira de coroação).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

from game.constants import (
    WHITE, BLACK,
    NEIGHBORS, DIAG_RAYS,
    BIT_TO_ROWCOL,
    PROMOTE_WHITE, PROMOTE_BLACK,
    WHITE_FORWARD_DIRS, BLACK_FORWARD_DIRS, ALL_DIRS,
)
from game.bitboard import iter_bits, test_bit, bit


# ─────────────────────────────────────────────────────────────────────────────
# (A) Definição da ação: Move representa uma ação a ∈ A(s)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Move:
    """Representa um movimento (simples ou captura múltipla)."""
    from_sq:   int
    to_sq:     int
    captured:  tuple = field(default_factory=tuple)  # bits das peças capturadas
    path:      tuple = field(default_factory=tuple)  # casas intermediárias visitadas

    @property
    def is_capture(self) -> bool:
        return len(self.captured) > 0

    def __repr__(self):
        coords = lambda b: BIT_TO_ROWCOL[b]
        if self.is_capture:
            return f"Move({coords(self.from_sq)} x{len(self.captured)} -> {coords(self.to_sq)})"
        return f"Move({coords(self.from_sq)} -> {coords(self.to_sq)})"


# ─────────────────────────────────────────────────────────────────────────────
# Funções auxiliares
# ─────────────────────────────────────────────────────────────────────────────

def _is_king(sq: int, kings_bb: int) -> bool:
    return test_bit(kings_bb, sq)


def _is_enemy(sq: int, own_bb: int, enemy_bb: int) -> bool:
    return test_bit(enemy_bb, sq) and not test_bit(own_bb, sq)


def _occupied(sq: int, own_bb: int, enemy_bb: int) -> bool:
    return test_bit(own_bb | enemy_bb, sq)


# ─────────────────────────────────────────────────────────────────────────────
# Capturas de pedra comum
# ─────────────────────────────────────────────────────────────────────────────

def _piece_captures_dfs(
    sq: int,
    own_bb: int,
    enemy_bb: int,
    kings_bb: int,
    captured_so_far: set,
    path_so_far: list,
    is_king: bool,
    all_sequences: list,
):
    """
    DFS recursiva para enumerar TODAS as sequências de captura a partir de `sq`.
    Modifica `all_sequences` com listas [list_of_captured_bits, final_sq, path].
    """
    dirs = ALL_DIRS if is_king else ALL_DIRS  # pedras também podem capturar para trás nas Damas Brasileiras

    found_any = False

    if is_king:
        for d in ALL_DIRS:
            ray = DIAG_RAYS[sq][d]
            # procura inimigo ao longo do raio
            for i, enemy_sq in enumerate(ray):
                if test_bit(own_bb, enemy_sq):
                    break  # bloqueado por aliado
                if test_bit(enemy_bb, enemy_sq):
                    if enemy_sq in captured_so_far:
                        break  # já capturado nesta sequência
                    # precisa de ao menos uma casa vazia após o inimigo
                    landing_candidates = ray[i+1:]
                    if not landing_candidates:
                        break
                    for land_sq in landing_candidates:
                        if _occupied(land_sq, own_bb, enemy_bb) and land_sq not in captured_so_far:
                            break
                        if land_sq in captured_so_far:
                            # a casa de uma peça já capturada pode ser pousada (ela será removida no final)
                            pass
                        # verifica se land_sq está livre (desconsiderando peças já capturadas)
                        temp_enemy = enemy_bb
                        for c in captured_so_far:
                            temp_enemy &= ~(1 << c)
                        if not test_bit(own_bb | temp_enemy, land_sq) or land_sq in captured_so_far:
                            new_captured = captured_so_far | {enemy_sq}
                            new_path = path_so_far + [land_sq]
                            _piece_captures_dfs(
                                land_sq,
                                own_bb,
                                enemy_bb,
                                kings_bb,
                                new_captured,
                                new_path,
                                True,  # continua como dama
                                all_sequences,
                            )
                            found_any = True
                    break  # não pode saltar mais de uma peça por raio
    else:
        # pedra comum: captura em qualquer direção diagonal com salto de 1 casa
        for d in ALL_DIRS:
            enemy_sq = NEIGHBORS[sq][d]
            if enemy_sq is None:
                continue
            if not test_bit(enemy_bb, enemy_sq):
                continue
            if enemy_sq in captured_so_far:
                continue
            land_sq = NEIGHBORS[enemy_sq][d]
            if land_sq is None:
                continue
            # land_sq deve estar vazio (desconsiderando já capturadas)
            temp_enemy = enemy_bb
            for c in captured_so_far:
                temp_enemy &= ~(1 << c)
            if _occupied(land_sq, own_bb, temp_enemy):
                continue
            new_captured = captured_so_far | {enemy_sq}
            new_path = path_so_far + [land_sq]
            _piece_captures_dfs(
                land_sq,
                own_bb,
                enemy_bb,
                kings_bb,
                new_captured,
                new_path,
                False,
                all_sequences,
            )
            found_any = True

    if not found_any and captured_so_far:
        # sequência terminada – registra
        all_sequences.append((list(captured_so_far), path_so_far[-1] if path_so_far else sq, path_so_far))


def _generate_captures(
    own_bb: int,
    enemy_bb: int,
    kings_bb: int,
    from_sq: int,
) -> list[Move]:
    """Gera todas as sequências de captura para a peça em `from_sq`."""
    is_king = test_bit(kings_bb, from_sq)
    all_sequences: list = []
    _piece_captures_dfs(
        from_sq, own_bb, enemy_bb, kings_bb,
        set(), [from_sq], is_king, all_sequences
    )
    moves = []
    for captured_list, final_sq, full_path in all_sequences:
        # full_path inclui from_sq como primeiro elemento e final_sq no fim
        intermediate = tuple(full_path[:-1])
        moves.append(Move(
            from_sq=from_sq,
            to_sq=final_sq,
            captured=tuple(sorted(captured_list)),
            path=intermediate,
        ))
    return moves


# ─────────────────────────────────────────────────────────────────────────────
# Movimentos simples
# ─────────────────────────────────────────────────────────────────────────────

def _generate_simple_moves(
    own_bb: int,
    enemy_bb: int,
    kings_bb: int,
    from_sq: int,
    player: int,
) -> list[Move]:
    """Gera movimentos simples (sem captura) para a peça em `from_sq`."""
    is_king = test_bit(kings_bb, from_sq)
    empty_bb = ~(own_bb | enemy_bb) & 0xFFFFFFFF
    moves = []

    if is_king:
        for d in ALL_DIRS:
            for to_sq in DIAG_RAYS[from_sq][d]:
                if not test_bit(empty_bb, to_sq):
                    break  # bloqueado
                moves.append(Move(from_sq=from_sq, to_sq=to_sq))
    else:
        fwd_dirs = WHITE_FORWARD_DIRS if player == WHITE else BLACK_FORWARD_DIRS
        for d in fwd_dirs:
            to_sq = NEIGHBORS[from_sq][d]
            if to_sq is not None and test_bit(empty_bb, to_sq):
                moves.append(Move(from_sq=from_sq, to_sq=to_sq))

    return moves


# ─────────────────────────────────────────────────────────────────────────────
# (A) Geração de ações: A(s) = generate_moves(s) → list[Move]
# ─────────────────────────────────────────────────────────────────────────────

def generate_moves(
    own_bb: int,
    enemy_bb: int,
    kings_bb: int,
    player: int,
) -> list[Move]:
    """
    Gera todos os movimentos legais para o jogador `player`.

    Aplica captura obrigatória e Lei da Maioria:
    - Se existe alguma captura, retorna APENAS capturas.
    - Dentre as capturas, retorna APENAS as com o maior número de peças capturadas.
    """
    all_captures: list[Move] = []

    for from_sq in iter_bits(own_bb):
        all_captures.extend(_generate_captures(own_bb, enemy_bb, kings_bb, from_sq))

    if all_captures:
        # Lei da Maioria: filtrar pelo máximo de capturas
        max_captures = max(len(m.captured) for m in all_captures)
        return [m for m in all_captures if len(m.captured) == max_captures]

    # Sem capturas: movimentos simples
    simple: list[Move] = []
    for from_sq in iter_bits(own_bb):
        simple.extend(_generate_simple_moves(own_bb, enemy_bb, kings_bb, from_sq, player))

    return simple


def will_promote(sq: int, player: int) -> bool:
    """Verifica se a casa `sq` é a fileira de promoção para `player`."""
    if player == WHITE:
        return test_bit(PROMOTE_WHITE, sq)
    return test_bit(PROMOTE_BLACK, sq)
