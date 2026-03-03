"""
Utilitários para operações com Bitboards de 32 bits.
"""

MASK32 = 0xFFFFFFFF


def bit(index: int) -> int:
    """Retorna um bitboard com apenas o bit `index` ativado."""
    return 1 << index


def set_bit(bb: int, index: int) -> int:
    return (bb | (1 << index)) & MASK32


def clear_bit(bb: int, index: int) -> int:
    return bb & ~(1 << index)


def test_bit(bb: int, index: int) -> bool:
    return bool(bb & (1 << index))


def popcount(bb: int) -> int:
    """Conta a quantidade de bits 1 (bin(n).count('1') é O(bits))."""
    return bin(bb).count('1')


def lsb(bb: int) -> int:
    """Índice do bit menos significativo. bb deve ser != 0."""
    return (bb & -bb).bit_length() - 1


def iter_bits(bb: int):
    """Gerador que itera sobre os índices dos bits 1 de menor para maior."""
    while bb:
        b = lsb(bb)
        yield b
        bb &= bb - 1  # limpa o LSB


def bb_to_set(bb: int) -> set[int]:
    """Converte um bitboard para um conjunto de índices."""
    return set(iter_bits(bb))


def set_to_bb(indices) -> int:
    """Converte um iterável de índices para um bitboard."""
    result = 0
    for i in indices:
        result |= (1 << i)
    return result
