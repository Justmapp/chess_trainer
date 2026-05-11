"""
Модуль move.py
==============
Містить клас Move, який інкапсулює усю інформацію про один шаховий хід:
координати початкової і цільової клітин, фігуру, що ходить, фігуру, що
вибивається (якщо є), а також спеціальні прапорці (рокіровка, взяття
«на проході», перетворення пішака).
"""

from chess_engine.pieces import Piece


class Move:
    """
    Опис одного шахового ходу.

    Атрибути:
        from_pos (tuple[int,int]): початкова клітина (ряд, стовпець);
        to_pos   (tuple[int,int]): цільова клітина (ряд, стовпець);
        piece (Piece): фігура, що ходить (на момент ходу);
        captured (Piece|None): фігура, що знімається з дошки (або None);
        is_castle_kingside (bool): рокіровка у короткий бік;
        is_castle_queenside (bool): рокіровка у довгий бік;
        is_en_passant (bool): взяття «на проході»;
        promotion (str|None): літера фігури-перетворення ("Q","R","B","N")
                              або None, якщо перетворення немає.
    """

    __slots__ = (
        "from_pos", "to_pos", "piece", "captured",
        "is_castle_kingside", "is_castle_queenside",
        "is_en_passant", "promotion",
        # Поля для відкату ходу:
        "_prev_en_passant_target", "_prev_has_moved", "_captured_pos",
        "_prev_halfmove_clock"
    )

    def __init__(self,
                 from_pos: tuple[int, int],
                 to_pos: tuple[int, int],
                 piece: Piece,
                 captured: Piece | None = None,
                 is_castle_kingside: bool = False,
                 is_castle_queenside: bool = False,
                 is_en_passant: bool = False,
                 promotion: str | None = None) -> None:
        self.from_pos = from_pos
        self.to_pos = to_pos
        self.piece = piece
        self.captured = captured
        self.is_castle_kingside = is_castle_kingside
        self.is_castle_queenside = is_castle_queenside
        self.is_en_passant = is_en_passant
        self.promotion = promotion
        # Службові поля заповнюються під час make_move (для undo_move).
        self._prev_en_passant_target = None
        self._prev_has_moved = None
        self._captured_pos = None
        self._prev_halfmove_clock = 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Move):
            return False
        return (self.from_pos == other.from_pos and
                self.to_pos == other.to_pos and
                self.promotion == other.promotion)

    def __hash__(self) -> int:
        return hash((self.from_pos, self.to_pos, self.promotion))

    def __repr__(self) -> str:
        from chess_engine.board import Board
        return f"Move({Board.square_name(*self.from_pos)}->" \
               f"{Board.square_name(*self.to_pos)})"

    def to_algebraic(self) -> str:
        """
        Повертає просту алгебричну нотацію ходу (без позначок шаху/мату).
        Приклади: e2e4, g1f3, e7e8Q (перетворення).
        """
        from chess_engine.board import Board
        s = Board.square_name(*self.from_pos) + Board.square_name(*self.to_pos)
        if self.promotion:
            s += self.promotion
        return s
