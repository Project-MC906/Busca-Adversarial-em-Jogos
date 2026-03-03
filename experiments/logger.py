"""
Sistema de logging para jogos, torneios e experimentos.

Registra dados importantes:
  - Tempo por jogada de cada jogador
  - Tempo médio total
  - Tipo de vitória (WHITE_WIN, BLACK_WIN, DRAW)
  - Número de peças final de cada lado
  - Identificação dos agentes/heurísticas
"""

from __future__ import annotations
import json
import csv
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Optional


# ── Data classes para diferentes tipos de log ──────────────────────────────────

@dataclass
class MoveLog:
    """Log de uma jogada individual."""
    move_number: int
    player: str        # 'WHITE' ou 'BLACK'
    move_notation: str  # ex: "(5,0) → (4,1)"
    time_s: float
    nodes_expanded: int
    depth_reached: int
    score: int
    white_pieces: int
    black_pieces: int


@dataclass
class GameLog:
    """Log completo de uma partida."""
    timestamp: str
    game_id: str
    white_player: str   # nome/heurística
    black_player: str
    result: str         # 'WHITE_WIN', 'BLACK_WIN', 'DRAW'
    total_moves: int
    white_pieces_final: int
    black_pieces_final: int
    total_time_s: float
    avg_time_per_move_s: float
    white_avg_time_s: float
    black_avg_time_s: float
    white_avg_nodes: int
    black_avg_nodes: int
    white_avg_depth: int
    black_avg_depth: int
    moves: list[MoveLog] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        """Converte para dicionário (sem a lista detalhada de moves)."""
        d = asdict(self)
        d['moves_count'] = len(self.moves)
        d.pop('moves')  # remove a lista grande
        return d


@dataclass
class TournamentLog:
    """Log de um torneio."""
    timestamp: str
    tournament_id: str
    player_a: str
    player_b: str
    total_games: int
    wins_a: int
    wins_b: int
    draws: int
    duration_s: float
    games: list[GameLog] = field(default_factory=list)


# ── Logger ────────────────────────────────────────────────────────────────────

class GameLogger:
    """Gerencia logs de jogos com suporte a CSV e JSON."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.games_dir = self.log_dir / "games"
        self.tournaments_dir = self.log_dir / "tournaments"
        self.games_dir.mkdir(exist_ok=True)
        self.tournaments_dir.mkdir(exist_ok=True)

    def save_game(self, game_log: GameLog, format: str = "json"):
        """Salva log da partida em JSON e CSV."""
        timestamp = game_log.timestamp.replace(" ", "_").replace(":", "-")
        basename = f"{timestamp}_{game_log.game_id}"

        if format in ("json", "both"):
            json_path = self.games_dir / f"{basename}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(game_log.to_dict(), f, indent=2, ensure_ascii=False)

        if format in ("csv", "both"):
            csv_path = self.games_dir / f"{basename}_summary.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=game_log.to_dict().keys())
                writer.writeheader()
                writer.writerow(game_log.to_dict())

            # CSV detalhado com movimentos
            csv_moves = self.games_dir / f"{basename}_moves.csv"
            if game_log.moves:
                with open(csv_moves, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=asdict(game_log.moves[0]).keys())
                    writer.writeheader()
                    for move in game_log.moves:
                        writer.writerow(asdict(move))

        return basename

    def save_tournament(self, tournament_log: TournamentLog, format: str = "json"):
        """Salva log do torneio."""
        timestamp = tournament_log.timestamp.replace(" ", "_").replace(":", "-")
        basename = f"{timestamp}_{tournament_log.tournament_id}"

        if format in ("json", "both"):
            json_path = self.tournaments_dir / f"{basename}.json"
            data = {
                'timestamp': tournament_log.timestamp,
                'tournament_id': tournament_log.tournament_id,
                'player_a': tournament_log.player_a,
                'player_b': tournament_log.player_b,
                'total_games': tournament_log.total_games,
                'wins_a': tournament_log.wins_a,
                'wins_b': tournament_log.wins_b,
                'draws': tournament_log.draws,
                'duration_s': tournament_log.duration_s,
                'games_count': len(tournament_log.games),
            }
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        if format in ("csv", "both"):
            csv_path = self.tournaments_dir / f"{basename}_summary.csv"
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'tournament_id', 'player_a', 'player_b', 'total_games',
                    'wins_a', 'wins_b', 'draws', 'duration_s'
                ])
                writer.writeheader()
                writer.writerow({
                    'tournament_id': tournament_log.tournament_id,
                    'player_a': tournament_log.player_a,
                    'player_b': tournament_log.player_b,
                    'total_games': tournament_log.total_games,
                    'wins_a': tournament_log.wins_a,
                    'wins_b': tournament_log.wins_b,
                    'draws': tournament_log.draws,
                    'duration_s': tournament_log.duration_s,
                })

            # CSV com resumo de cada jogo
            csv_games = self.tournaments_dir / f"{basename}_games.csv"
            if tournament_log.games:
                with open(csv_games, "w", newline="", encoding="utf-8") as f:
                    writer = csv.DictWriter(f, fieldnames=tournament_log.games[0].to_dict().keys())
                    writer.writeheader()
                    for game in tournament_log.games:
                        writer.writerow(game.to_dict())

        return basename

    def get_log_files(self):
        """Lista todos os arquivos de log."""
        return {
            'games': list(self.games_dir.glob("*.json")) + list(self.games_dir.glob("*.csv")),
            'tournaments': list(self.tournaments_dir.glob("*.json")) + list(self.tournaments_dir.glob("*.csv")),
        }


# ── Factory global ────────────────────────────────────────────────────────────

_logger_instance: Optional[GameLogger] = None


def get_logger(log_dir: str = "logs") -> GameLogger:
    """Retorna a instância global do logger."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = GameLogger(log_dir)
    return _logger_instance


def init_logger(log_dir: str = "logs") -> GameLogger:
    """Inicializa o logger global."""
    global _logger_instance
    _logger_instance = GameLogger(log_dir)
    return _logger_instance
