"""
Conversões entre coordenadas (row, col) e notação de xadrez.
"""

def rowcol_to_chess(row: int, col: int) -> str:
    """
    Converte (row, col) (0-7, 0-7) para notação de xadrez (ex: 'a8', 'h1').
    
    Mapeamento:
      - Coluna: 0→a, 1→b, ..., 7→h
      - Linha: 0→8, 1→7, ..., 7→1 (invertida)
    """
    col_letter = chr(ord('a') + col)
    row_number = 8 - row
    return f"{col_letter}{row_number}"


def chess_to_rowcol(notation: str) -> tuple[int, int] | None:
    """
    Converte notação de xadrez (ex: 'a8', 'h1') para (row, col).
    Retorna None se inválido.
    
    Exemplo:
      chess_to_rowcol('a8') → (0, 0)
      chess_to_rowcol('h1') → (7, 7)
    """
    notation = notation.strip().lower()
    if len(notation) != 2:
        return None
    
    col_letter, row_number = notation[0], notation[1]
    
    if col_letter < 'a' or col_letter > 'h':
        return None
    if row_number < '1' or row_number > '8':
        return None
    
    col = ord(col_letter) - ord('a')
    row = 8 - int(row_number)
    return row, col
