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
CENTER_BONUS        = 40   # pontos por peça no centro  (era 10)

# Bônus de borda (colunas 0 e 7): peças laterais são difíceis de capturar
EDGE_BONUS          = 2    # pontos por peça na borda lateral  (era 5)

# Bônus de avanço: por fileira percorrida em direção à promoção
ADVANCE_BONUS_PER_ROW = 20  # multiplicado pelo número de fileiras avançadas  (era 5)

# ── h3: Posicional (componente interno) + Mobilidade ─────────────────────────
# Pesos posicionais usados pela parte posicional de h3 (independentes de h2)
CENTER_BONUS_H3        = 10   # pontos por peça no centro
EDGE_BONUS_H3          = 5    # pontos por peça na borda lateral
ADVANCE_BONUS_PER_ROW_H3 = 5  # multiplicado pelo número de fileiras avançadas

# Diferença no número de movimentos legais disponíveis
MOBILITY_WEIGHT = 1   # multiplicado por (meus_movimentos - movimentos_adversário)  (era 3)

# ── h4: Conectividade e Ameaças ───────────────────────────────────────────────
SUPPORT_BONUS     = 15    # por cada vizinho diagonal amigo (peças apoiadas)
ISOLATION_PENALTY = 20    # penalidade por peça sem nenhum apoio
THREAT_BONUS      = 40    # por cada peça inimiga ameaçada de captura imediata
MATERIAL_WEIGHT_H4 = 0.1  # fator leve de material como desempate em h4
