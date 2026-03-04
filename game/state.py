"""
Estado do jogo de Damas Brasileiras com representação Bitboard.

Modelagem formal do jogo como (S, A, T, U):
  S – conjunto de estados (GameState): ver classe GameState abaixo
  A – ações legais (Move): ver game/moves.py e GameState.get_moves()
  T – função de transição: ver GameState.apply_move()
  U – função de utilidade: ver GameState.utility()

Estado encapsula:
  white_bb   – bitboard das peças brancas (pedras + damas)
  black_bb   – bitboard das peças pretas  (pedras + damas)
  kings_bb   – bitboard de todas as damas (qualquer cor)
  turn       – WHITE (+1) ou BLACK (-1)
  no_progress – contador de lances sem captura nem avanço de pedra (regra de empate)

A interface compatível com os algoritmos:
  state.get_moves()        → list[Move]
  state.apply_move(move)   → GameState
  state.is_terminal()      → bool
  state.utility()          → int (+INF vitória branca, -INF vitória preta, 0 empate)
"""

from __future__ import annotations
from functools import cached_property

from game.constants import (
    WHITE, BLACK,
    WHITE_START, BLACK_START,
    PROMOTE_WHITE, PROMOTE_BLACK,
    DRAW_MOVE_LIMIT, INF,
    BIT_TO_ROWCOL,
)
from game.bitboard import test_bit, popcount, iter_bits
from game.moves import Move, generate_moves, will_promote


class GameState:
    """Representação imutável do estado do jogo."""

    # (S) Representação do estado: três bitboards + turno + contador de progresso
    __slots__ = (
        'white_bb', 'black_bb', 'kings_bb',
        'turn', 'no_progress',
        '_moves_cache', '_terminal_cache', '_hash_cache',
    )

    def __init__(
        self,
        white_bb: int,
        black_bb: int,
        kings_bb: int,
        turn: int = WHITE,
        no_progress: int = 0,
    ):
        self.white_bb    = white_bb
        self.black_bb    = black_bb
        self.kings_bb    = kings_bb
        self.turn        = turn
        self.no_progress = no_progress
        self._moves_cache:    list[Move] | None = None
        self._terminal_cache: bool        | None = None
        self._hash_cache:     int         | None = None

    # ── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    def initial(cls) -> GameState:
        """Estado inicial padrão das Damas Brasileiras."""
        return cls(
            white_bb   = WHITE_START,
            black_bb   = BLACK_START,
            kings_bb   = 0,
            turn       = WHITE,
            no_progress= 0,
        )

    # ── Propriedades úteis ────────────────────────────────────────────────────

    @property
    def own_bb(self) -> int:
        return self.white_bb if self.turn == WHITE else self.black_bb

    @property
    def enemy_bb(self) -> int:
        return self.black_bb if self.turn == WHITE else self.white_bb

    @property
    def white_count(self) -> int:
        return popcount(self.white_bb)

    @property
    def black_count(self) -> int:
        return popcount(self.black_bb)

    @property
    def white_kings(self) -> int:
        return popcount(self.white_bb & self.kings_bb)

    @property
    def black_kings(self) -> int:
        return popcount(self.black_bb & self.kings_bb)

    # ── Interface principal ────────────────────────────────────────────────────

    # (A) Geração de ações: retorna todas as ações legais do estado atual
    def get_moves(self) -> list[Move]:
        if self._moves_cache is None:
            self._moves_cache = generate_moves(
                self.own_bb, self.enemy_bb, self.kings_bb, self.turn
            )
        return self._moves_cache

    # (T) Função de transição: T(s, a) → s'  (retorna novo estado imutável)
    def apply_move(self, move: Move) -> GameState:
        """Aplica um movimento e retorna o novo estado (imutável)."""
        w = self.white_bb
        b = self.black_bb
        k = self.kings_bb

        from_bb = 1 << move.from_sq
        to_bb   = 1 << move.to_sq

        # Remove peça capturadas do inimigo
        captured_bb = 0
        for sq in move.captured:
            captured_bb |= (1 << sq)

        is_capture = bool(move.captured)

        if self.turn == WHITE:
            w = (w & ~from_bb) | to_bb
            b = b & ~captured_bb
        else:
            b = (b & ~from_bb) | to_bb
            w = w & ~captured_bb

        # Atualiza bitboard de damas: remove from, capturadas; copia status de dama
        was_king = test_bit(self.kings_bb, move.from_sq)
        k = k & ~from_bb & ~captured_bb

        if was_king:
            k |= to_bb
        else:
            # Verifica promoção: apenas se o destino final for a fileira de coroação
            if will_promote(move.to_sq, self.turn):
                k |= to_bb

        # Contador de progresso:
        # resetar se houve captura OU se pedra comum avançou (não era dama)
        if is_capture or (not was_king and not test_bit(k, to_bb.bit_length() - 1)):
            # Simplificado: reseta se houve captura — avanço de pedra é sempre progresso
            no_prog = 0
        elif is_capture:
            no_prog = 0
        else:
            no_prog = self.no_progress + 1

        # Regra de empate: pedra vorou / dama se moveu sem captura → incrementa
        # Simplificação correta: incrementa se não houve captura E não houve promoção nova
        if not is_capture:
            no_prog = self.no_progress + 1
        else:
            no_prog = 0

        return GameState(
            white_bb    = w,
            black_bb    = b,
            kings_bb    = k,
            turn        = -self.turn,
            no_progress = no_prog,
        )

    # Teste de terminal: verifica se o estado é final (sem peças, sem movimentos ou empate)
    def is_terminal(self) -> bool:
        if self._terminal_cache is None:
            if self.no_progress >= DRAW_MOVE_LIMIT:
                self._terminal_cache = True
            elif self.white_bb == 0 or self.black_bb == 0:
                self._terminal_cache = True
            else:
                self._terminal_cache = len(self.get_moves()) == 0
        return self._terminal_cache

    # (U) Função de utilidade: U(s) → +INF (brancas vencem), -INF (pretas vencem), 0 (empate)
    def utility(self) -> int:
        """
        Retorna o valor terminal do estado (apenas chamar quando is_terminal() == True).
        +INF = vitória branca, -INF = vitória preta, 0 = empate.
        """
        if self.no_progress >= DRAW_MOVE_LIMIT:
            return 0
        if self.white_bb == 0:
            return -INF
        if self.black_bb == 0:
            return +INF
        # sem movimentos legais → quem está sem movimento perde
        if self.turn == WHITE:
            return -INF   # brancas não têm movimentos → perde
        return +INF        # pretas não têm movimentos → brancas ganham

    # ── Eq / Hash (para tabelo de transposição) ────────────────────────────────

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, GameState)
            and self.white_bb    == other.white_bb
            and self.black_bb    == other.black_bb
            and self.kings_bb    == other.kings_bb
            and self.turn        == other.turn
        )

    def __hash__(self) -> int:
        if self._hash_cache is None:
            self._hash_cache = hash((
                self.white_bb, self.black_bb, self.kings_bb, self.turn
            ))
        return self._hash_cache

    # ── Debug ──────────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"GameState(W={self.white_count}pcs/{self.white_kings}damas "
            f"B={self.black_count}pcs/{self.black_kings}damas "
            f"turn={'WHITE' if self.turn==WHITE else 'BLACK'} "
            f"no_prog={self.no_progress})"
        )

    def board_str(self) -> str:
        """Representação textual do tabuleiro para debug."""
        grid = [['.' for _ in range(8)] for _ in range(8)]
        for bit_idx in iter_bits(self.white_bb):
            r, c = BIT_TO_ROWCOL[bit_idx]
            grid[r][c] = 'K' if test_bit(self.kings_bb, bit_idx) else 'w'
        for bit_idx in iter_bits(self.black_bb):
            r, c = BIT_TO_ROWCOL[bit_idx]
            grid[r][c] = 'Q' if test_bit(self.kings_bb, bit_idx) else 'b'
        lines = []
        lines.append('  0 1 2 3 4 5 6 7')
        for r, row in enumerate(grid):
            lines.append(f"{r} {' '.join(row)}")
        return '\n'.join(lines)
