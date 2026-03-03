"""
Move Ordering para maximizar a eficiência do Alpha-Beta Pruning.

Hierarquia de ordenação (maior prioridade primeiro):
  1. Hash Move (melhor lance da Tabela de Transposição)
  2. Capturas (mais capturas > menos; captura de dama > captura de pedra)
  3. Killer Moves (lances quietos que causaram beta-cutoffs em nós irmãos)
  4. History Heuristic (lances que historicamente causaram cutoffs)
  5. Demais movimentos simples (ordenados por destino central)
"""

from __future__ import annotations
from game.moves import Move
from game.bitboard import test_bit
from game.constants import CENTER_BITS, KING_VALUE, PIECE_VALUE


# ── Killer Moves ──────────────────────────────────────────────────────────────

class KillerMoves:
    """Mantém 2 killer moves por profundidade."""

    def __init__(self, max_depth: int = 64):
        self.killers: list[list[Move | None]] = [[None, None] for _ in range(max_depth)]

    def store(self, move: Move, depth: int):
        if depth >= len(self.killers):
            return
        if move != self.killers[depth][0]:
            self.killers[depth][1] = self.killers[depth][0]
            self.killers[depth][0] = move

    def is_killer(self, move: Move, depth: int) -> bool:
        if depth >= len(self.killers):
            return False
        return move in self.killers[depth]

    def clear(self):
        for slot in self.killers:
            slot[0] = slot[1] = None


# ── History Heuristic ─────────────────────────────────────────────────────────

class HistoryTable:
    """Tabela de história indexada por (from_sq, to_sq)."""

    def __init__(self):
        # 32 × 32 = 1024 entradas
        self._table: dict[tuple[int, int], int] = {}

    def update(self, move: Move, depth: int):
        key = (move.from_sq, move.to_sq)
        self._table[key] = self._table.get(key, 0) + depth * depth

    def score(self, move: Move) -> int:
        return self._table.get((move.from_sq, move.to_sq), 0)

    def clear(self):
        self._table.clear()


# ── Score de ordenação ─────────────────────────────────────────────────────────

def _capture_score(move: Move, enemy_bb: int, kings_bb: int) -> int:
    """Score de valor de captura: damas valem mais que pedras."""
    score = len(move.captured) * 1000
    for cap in move.captured:
        if test_bit(kings_bb, cap):
            score += KING_VALUE
        else:
            score += PIECE_VALUE
    return score


def _destination_score(move: Move) -> int:
    """Bônus para destinos centrais."""
    return 10 if move.to_sq in CENTER_BITS else 0


# ── Função principal de ordenação ─────────────────────────────────────────────

def order_moves(
    moves: list[Move],
    enemy_bb: int,
    kings_bb: int,
    depth: int,
    hash_move: Move | None,
    killers: KillerMoves,
    history: HistoryTable,
) -> list[Move]:
    """
    Ordena a lista de movimentos de acordo com a heurística de move ordering.
    Retorna nova lista ordenada do mais promissor ao menos.
    """
    def score(m: Move) -> int:
        # 1. Hash move: prioridade máxima
        if hash_move is not None and m == hash_move:
            return 10_000_000

        # 2. Capturas
        if m.is_capture:
            return 1_000_000 + _capture_score(m, enemy_bb, kings_bb)

        # 3. Killer moves
        if killers.is_killer(m, depth):
            return 900_000

        # 4. History heuristic
        hist_score = history.score(m)
        if hist_score > 0:
            return 800_000 + min(hist_score, 99_999)

        # 5. Movimentos simples com bônus central
        return _destination_score(m)

    return sorted(moves, key=score, reverse=True)
