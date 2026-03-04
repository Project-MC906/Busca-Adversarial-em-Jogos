"""
Pesos das heurísticas — arquivo central de configuração.

Edite este arquivo para experimentar com os pesos das heurísticas.
Todas as funções de avaliação (h1–h4) importam seus pesos daqui.

─── h1: Material ────────────────────────────────────────────────────────────
  Peça comum e dama. Também usado em move ordering.
"""

# ── h1: Material ──────────────────────────────────────────────────────────────
PIECE_VALUE = 100   # valor de uma pedra comum
KING_VALUE  = 300   # valor de uma dama (flying king)

# ── h2: Posicional ────────────────────────────────────────────────────────────
# Bônus de centro: peças nas 8 casas centrais
CENTER_BONUS        = 10   # pontos por peça no centro

# Bônus de borda (colunas 0 e 7): peças laterais são difíceis de capturar
EDGE_BONUS          = 5    # pontos por peça na borda lateral

# Bônus de avanço: por fileira percorrida em direção à promoção
ADVANCE_BONUS_PER_ROW = 5  # multiplicado pelo número de fileiras avançadas

# ── h3: Mobilidade ────────────────────────────────────────────────────────────
# Diferença no número de movimentos legais disponíveis
MOBILITY_WEIGHT = 3   # multiplicado por (meus_movimentos - movimentos_adversário)

# ── h4: Conectividade e Ameaças ───────────────────────────────────────────────
SUPPORT_BONUS     = 15    # por cada vizinho diagonal amigo (peças apoiadas)
ISOLATION_PENALTY = 20    # penalidade por peça sem nenhum apoio
THREAT_BONUS      = 40    # por cada peça inimiga ameaçada de captura imediata
MATERIAL_WEIGHT_H4 = 0.1  # fator leve de material como desempate em h4
