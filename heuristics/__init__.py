# Heuristic evaluation functions for Damas Brasileiras
from heuristics.material   import evaluate_material
from heuristics.positional import evaluate_positional
from heuristics.full       import evaluate_full

__all__ = ['evaluate_material', 'evaluate_positional', 'evaluate_full']
