"""
Tabela de Transposição com Zobrist Hashing para Damas Brasileiras.

Zobrist table:  zobrist_table[bit][piece_type]
  piece_type: 0 = peça branca, 1 = dama branca, 2 = peça preta, 3 = dama preta
  + zobrist_turn: XOR quando é turno das pretas.

Política de substituição: Depth-Preferred
  (substitui somente se profundidade nova >= existente).
"""

from __future__ import annotations
import random
from typing import Optional

from game.constants import WHITE, BLACK
from game.bitboard import iter_bits, test_bit


# ── Tipos de flags de nó ──────────────────────────────────────────────────────
EXACT       = 0  # valor exato
LOWER_BOUND = 1  # alpha-cutoff: valor é pelo menos este (fail-high)
UPPER_BOUND = 2  # beta-cutoff:  valor é no máximo este (fail-low)


# ── Pré-computação da tabela Zobrist ─────────────────────────────────────────

_RAND = random.Random(42)   # seed fixo para reprodutibilidade

# Tipos de peça: índice para a tabela
_WP = 0   # white piece (pedra)
_WK = 1   # white king  (dama branca)
_BP = 2   # black piece (pedra)
_BK = 3   # black king  (dama preta)

ZOBRIST_TABLE: list[list[int]] = [
    [_RAND.getrandbits(64) for _ in range(4)]
    for _ in range(32)
]
ZOBRIST_TURN: int = _RAND.getrandbits(64)  # XOR quando vez das pretas


# ── Cálculo do hash ───────────────────────────────────────────────────────────

def compute_hash(state) -> int:
    """Computa o hash Zobrist completo de um GameState (O(n_peças))."""
    key = 0
    kings_bb = state.kings_bb
    for sq in iter_bits(state.white_bb):
        ptype = _WK if test_bit(kings_bb, sq) else _WP
        key ^= ZOBRIST_TABLE[sq][ptype]
    for sq in iter_bits(state.black_bb):
        ptype = _BK if test_bit(kings_bb, sq) else _BP
        key ^= ZOBRIST_TABLE[sq][ptype]
    if state.turn == BLACK:
        key ^= ZOBRIST_TURN
    return key


def hash_xor_piece(sq: int, is_king: bool, is_white: bool) -> int:
    """Retorna a contribuição XOR de uma peça específica (para hash incremental)."""
    if is_white:
        ptype = _WK if is_king else _WP
    else:
        ptype = _BK if is_king else _BP
    return ZOBRIST_TABLE[sq][ptype]


# ── Entrada da Tabela de Transposição ─────────────────────────────────────────

class TTEntry:
    """Entrada na tabela de transposição."""
    __slots__ = ('key', 'score', 'flag', 'depth', 'best_move')

    def __init__(self, key: int, score: int, flag: int, depth: int, best_move):
        self.key       = key
        self.score     = score
        self.flag      = flag
        self.depth     = depth
        self.best_move = best_move


# ── Tabela de Transposição ─────────────────────────────────────────────────────

class TranspositionTable:
    """
    Tabela de Transposição implementada como dicionário Python.
    Política de substituição: Depth-Preferred.
    """

    def __init__(self, max_size: int = 1_000_000):
        self._table: dict[int, TTEntry] = {}
        self.max_size = max_size
        self.hits     = 0
        self.misses   = 0
        self.stores   = 0

    def lookup(self, key: int, depth: int, alpha: int, beta: int):
        """
        Busca a entrada na TT.
        Retorna (score, best_move) se pode usar o valor, ou (None, best_move) se
        apenas o best_move é útil para ordering.
        """
        entry = self._table.get(key)
        if entry is None or entry.key != key:
            self.misses += 1
            return None, None

        best_move = entry.best_move
        if entry.depth < depth:
            # profundidade insuficiente – só usa best_move para ordering
            self.misses += 1
            return None, best_move

        self.hits += 1
        if entry.flag == EXACT:
            return entry.score, best_move
        if entry.flag == LOWER_BOUND and entry.score >= beta:
            return entry.score, best_move
        if entry.flag == UPPER_BOUND and entry.score <= alpha:
            return entry.score, best_move

        return None, best_move

    def store(self, key: int, score: int, flag: int, depth: int, best_move):
        """Armazena uma entrada. Usa política Depth-Preferred."""
        existing = self._table.get(key)
        if existing is not None and existing.key == key and existing.depth > depth:
            return  # não substitui entrada de maior profundidade

        if len(self._table) >= self.max_size and key not in self._table:
            # Limpeza simples: remove ~10% para evitar overhead alto
            to_remove = list(self._table.keys())[:self.max_size // 10]
            for k in to_remove:
                del self._table[k]

        self._table[key] = TTEntry(key, score, flag, depth, best_move)
        self.stores += 1

    def clear(self):
        self._table.clear()
        self.hits = self.misses = self.stores = 0

    @property
    def size(self) -> int:
        return len(self._table)

    def stats(self) -> dict:
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0.0
        return {
            'size':     self.size,
            'hits':     self.hits,
            'misses':   self.misses,
            'stores':   self.stores,
            'hit_rate': hit_rate,
        }
