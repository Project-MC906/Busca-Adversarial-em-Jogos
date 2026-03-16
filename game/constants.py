"""
Constantes para Damas Brasileiras com representação Bitboard (32 bits).

Layout do tabuleiro – casas escuras numeradas 0-31:
   Col:  0    1    2    3    4    5    6    7
Row 0:       [ 0]      [ 1]      [ 2]      [ 3]
Row 1: [ 4]       [ 5]      [ 6]      [ 7]
Row 2:       [ 8]      [ 9]      [10]      [11]
Row 3: [12]      [13]      [14]      [15]
Row 4:      [16]      [17]      [18]      [19]
Row 5: [20]      [21]      [22]      [23]
Row 6:      [24]      [25]      [26]      [27]
Row 7: [28]      [29]      [30]      [31]

- Brancas (WHITE) começam nas linhas 5-7 (bits 20-31), movem para cima (row decrescente).
- Pretas  (BLACK) começam nas linhas 0-2 (bits 0-11), movem para baixo (row crescente).
- Promoção branca: chegar na linha 0 (bits 0-3).
- Promoção preta:  chegar na linha 7 (bits 28-31).
"""

BOARD_MASK: int = 0xFFFFFFFF   # todos os 32 bits válidos

# ── Jogadores ───────────────────────────────────────────────────────────────
WHITE  = 1
BLACK  = -1

# ── Posições iniciais ────────────────────────────────────────────────────────
WHITE_START: int = 0xFFF00000  # bits 20-31
BLACK_START: int = 0x00000FFF  # bits 0-11

# ── Linhas de promoção ───────────────────────────────────────────────────────
PROMOTE_WHITE: int = 0x0000000F   # bits 0-3  (linha 0)
PROMOTE_BLACK: int = 0xF0000000   # bits 28-31 (linha 7)

# ── Mapeamento (row, col) ↔ bit ─────────────────────────────────────────────
# Linha par  (0,2,4,6): casas escuras nas colunas 1,3,5,7
# Linha ímpar(1,3,5,7): casas escuras nas colunas 0,2,4,6

def _make_tables():
    bit_to_rowcol = {}          # bit  → (row, col)
    rowcol_to_bit = {}          # (row,col) → bit
    b = 0
    for row in range(8):
        if row % 2 == 0:        # linha par: cols 1,3,5,7
            cols = [1, 3, 5, 7]
        else:                   # linha ímpar: cols 0,2,4,6
            cols = [0, 2, 4, 6]
        for col in cols:
            bit_to_rowcol[b] = (row, col)
            rowcol_to_bit[(row, col)] = b
            b += 1
    return bit_to_rowcol, rowcol_to_bit

BIT_TO_ROWCOL, ROWCOL_TO_BIT = _make_tables()

def rowcol_to_bit_safe(row: int, col: int) -> int | None:
    """Retorna índice do bit para (row, col) ou None se fora do tabuleiro."""
    if 0 <= row < 8 and 0 <= col < 8:
        return ROWCOL_TO_BIT.get((row, col))
    return None

# ── Tabelas de vizinhos pré-computadas ───────────────────────────────────────
# Para cada bit, os 4 vizinhos diagonais: NW, NE, SW, SE (None = fora).
# N = row decrescente (direção de avanço branco)
# NW = (row-1, col-1), NE = (row-1, col+1)
# SW = (row+1, col-1), SE = (row+1, col+1)

NEIGHBORS: list[dict] = []  # NEIGHBORS[bit] = {'NW':b|None, 'NE':b|None, 'SW':b|None, 'SE':b|None}

def _make_neighbors():
    nb = []
    dirs = {'NW': (-1, -1), 'NE': (-1, +1), 'SW': (+1, -1), 'SE': (+1, +1)}
    for bit in range(32):
        row, col = BIT_TO_ROWCOL[bit]
        entry = {}
        for d, (dr, dc) in dirs.items():
            entry[d] = rowcol_to_bit_safe(row + dr, col + dc)
        nb.append(entry)
    return nb

NEIGHBORS = _make_neighbors()

# Para cada bit, todas as casas ao longo de cada diagonal (para damas voadoras).
# DIAG_RAY[bit][dir] = lista ordenada de bits na direção dir, da mais próxima à mais distante.
DIAG_RAYS: list[dict] = []

def _make_diag_rays():
    rays = []
    dirs = {'NW': (-1, -1), 'NE': (-1, +1), 'SW': (+1, -1), 'SE': (+1, +1)}
    for bit in range(32):
        row, col = BIT_TO_ROWCOL[bit]
        entry = {}
        for d, (dr, dc) in dirs.items():
            ray = []
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                b = ROWCOL_TO_BIT.get((r, c))
                if b is not None:
                    ray.append(b)
                r += dr
                c += dc
            entry[d] = ray
        rays.append(entry)
    return rays

DIAG_RAYS = _make_diag_rays()

# ── Direções de avanço por jogador ────────────────────────────────────────────
WHITE_FORWARD_DIRS = ('NW', 'NE')   # brancas movem para linha 0
BLACK_FORWARD_DIRS = ('SW', 'SE')   # pretas  movem para linha 7
ALL_DIRS = ('NW', 'NE', 'SW', 'SE')

# ── Valores da função de avaliação ────────────────────────────────────────────
PIECE_VALUE  = 80
KING_VALUE   = 240
INF          = 10_000_000

# ── Limite de empate (20 lances sem captura ou avanço de pedra) ───────────────
DRAW_MOVE_LIMIT = 20


CENTER_BITS = frozenset([
    ROWCOL_TO_BIT[(3, 2)], ROWCOL_TO_BIT[(3, 4)],
    ROWCOL_TO_BIT[(4,3)], ROWCOL_TO_BIT[(4, 5)]
])

FOUR_CENTER_BITS = frozenset([
    ROWCOL_TO_BIT[(3, 2)], ROWCOL_TO_BIT[(3, 4)],
    ROWCOL_TO_BIT[(4,3)], ROWCOL_TO_BIT[(4, 5)]
])

SIX_CENTER_BITS = frozenset([
    ROWCOL_TO_BIT[(3, 2)], ROWCOL_TO_BIT[(3, 4)],
    ROWCOL_TO_BIT[(3, 6)], ROWCOL_TO_BIT[(4, 1)],
    ROWCOL_TO_BIT[(4, 3)], ROWCOL_TO_BIT[(4, 5)],
])

EIGHT_CENTER_BITS = frozenset([
    ROWCOL_TO_BIT[(3, 2)], ROWCOL_TO_BIT[(3, 4)],
    ROWCOL_TO_BIT[(3, 6)], ROWCOL_TO_BIT[(4, 1)],
    ROWCOL_TO_BIT[(4, 3)], ROWCOL_TO_BIT[(4, 5)],
    ROWCOL_TO_BIT[(3,0)], ROWCOL_TO_BIT[(4,7)],
])



CENTER_BONUS = 10

# Bônus de borda (proteção lateral)
EDGE_COLS = frozenset([0, 7])
EDGE_BONUS = 0

# Bônus de avanço (por fileiras percorridas)
ADVANCE_BONUS_PER_ROW = 5  # por linha avançada em direção à promoção
