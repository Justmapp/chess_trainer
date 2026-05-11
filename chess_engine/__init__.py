"""
Пакет chess_engine
==================
Реалізація шахового двигуна:
    pieces.py  — ієрархія класів фігур;
    board.py   — клас Board (8x8 дошка);
    move.py    — клас Move (один хід);
    game.py    — клас GameState (правила, історія, мат/пат/нічия);
    ai.py      — клас ChessAI (мінімакс із альфа-бета відсіченнями).
"""

from chess_engine.pieces import (
    Piece, King, Queen, Rook, Bishop, Knight, Pawn,
    WHITE, BLACK, piece_from_letter
)
from chess_engine.board import Board
from chess_engine.move import Move
from chess_engine.game import GameState
from chess_engine.ai import ChessAI

__all__ = [
    "Piece", "King", "Queen", "Rook", "Bishop", "Knight", "Pawn",
    "WHITE", "BLACK", "piece_from_letter",
    "Board", "Move", "GameState", "ChessAI",
]
