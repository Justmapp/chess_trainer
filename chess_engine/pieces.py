"""
Модуль pieces.py
================
Містить ієрархію класів шахових фігур.

Базовий клас Piece є абстрактним і визначає спільний інтерфейс для усіх фігур.
Конкретні фігури (King, Queen, Rook, Bishop, Knight, Pawn) успадковують від
Piece та реалізують власний метод get_pseudo_legal_moves(), що повертає список
псевдо-легальних ходів (тобто ходів за правилами руху фігури, без перевірки
шахів власному королю).

Демонструє принципи ООП:
    - інкапсуляція (атрибути приховані за властивостями);
    - успадкування (King, Queen, Rook, Bishop, Knight, Pawn -> Piece);
    - поліморфізм (метод get_pseudo_legal_moves() перевизначається у нащадках).
"""

from abc import ABC, abstractmethod

# Константи кольорів. Використовуються по всьому проекту для уникнення помилок.
WHITE = "white"
BLACK = "black"


class Piece(ABC):
    """
    Абстрактний базовий клас для усіх шахових фігур.

    Атрибути:
        color (str): колір фігури ("white" або "black").
        has_moved (bool): чи робила фігура ходи (для рокіровки та подвійного
                          ходу пішака).
    """

    # Символ Юнікоду для відображення фігури (перевизначається у нащадках).
    SYMBOL_WHITE: str = "?"
    SYMBOL_BLACK: str = "?"
    # Чисельне значення фігури для оцінки позиції AI-двигуном.
    VALUE: int = 0
    # Коротка назва (для шахової нотації).
    NAME: str = "?"

    def __init__(self, color: str) -> None:
        """
        Ініціалізує фігуру із заданим кольором.

        :param color: "white" або "black"
        """
        if color not in (WHITE, BLACK):
            raise ValueError(f"Неприпустимий колір фігури: {color}")
        self._color = color
        self._has_moved = False

    # ---------- Властивості (інкапсуляція) ---------- #
    @property
    def color(self) -> str:
        """Колір фігури."""
        return self._color

    @property
    def has_moved(self) -> bool:
        """Прапорець, чи робила фігура хід."""
        return self._has_moved

    @has_moved.setter
    def has_moved(self, value: bool) -> None:
        self._has_moved = bool(value)

    @property
    def symbol(self) -> str:
        """Юнікод-символ фігури відповідного кольору."""
        return self.SYMBOL_WHITE if self._color == WHITE else self.SYMBOL_BLACK

    # ---------- Допоміжні методи ---------- #
    def is_enemy(self, other: "Piece | None") -> bool:
        """Повертає True, якщо other — фігура суперника."""
        return other is not None and other.color != self._color

    def is_ally(self, other: "Piece | None") -> bool:
        """Повертає True, якщо other — своя фігура."""
        return other is not None and other.color == self._color

    # ---------- Поліморфізм ---------- #
    @abstractmethod
    def get_pseudo_legal_moves(self, board, row: int, col: int) -> list[tuple[int, int]]:
        """
        Повертає список координат (row, col), куди ця фігура може зробити хід
        згідно правил її руху (без врахування шахів власному королю).

        :param board: екземпляр класу Board
        :param row: поточний ряд фігури (0..7)
        :param col: поточний стовпець фігури (0..7)
        :return: список цільових клітин у форматі (ряд, стовпець)
        """
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._color})"


# ---------- Допоміжна функція для лінійних фігур ---------- #
def _slide(board, row: int, col: int, color: str,
           directions: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """
    Допоміжна функція для розрахунку ходів "ковзаючих" фігур
    (Тура, Слон, Ферзь). Йде у вказаних напрямках доти, доки не натрапить
    на край дошки, свою фігуру (тоді не включає її) або на фігуру суперника
    (включає й зупиняється).

    :param board: дошка
    :param row, col: початкова клітина
    :param color: колір фігури-ходящої
    :param directions: список зміщень (dr, dc)
    :return: список цільових координат
    """
    moves: list[tuple[int, int]] = []
    for dr, dc in directions:
        r, c = row + dr, col + dc
        while 0 <= r < 8 and 0 <= c < 8:
            target = board.get_piece(r, c)
            if target is None:
                moves.append((r, c))
            elif target.color != color:
                moves.append((r, c))  # взяття
                break
            else:
                break  # своя фігура — стоп
            r += dr
            c += dc
    return moves


# =============================================================================
#                       Конкретні класи фігур
# =============================================================================


class King(Piece):
    """Король. Ходить на одну клітину у будь-якому напрямку."""

    SYMBOL_WHITE = "\u2654"  # ♔
    SYMBOL_BLACK = "\u265A"  # ♚
    VALUE = 20000           # умовно «нескінченність»
    NAME = "K"

    # Усі 8 напрямків навколо короля.
    _DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1),
                   (0, -1),           (0, 1),
                   (1, -1),  (1, 0),  (1, 1)]

    def get_pseudo_legal_moves(self, board, row: int, col: int) -> list[tuple[int, int]]:
        moves: list[tuple[int, int]] = []
        for dr, dc in self._DIRECTIONS:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target = board.get_piece(r, c)
                if target is None or target.color != self._color:
                    moves.append((r, c))
        # Рокіровка обчислюється у GameState (потрібна перевірка шаху на полях).
        return moves


class Queen(Piece):
    """Ферзь. Поєднує можливості тури і слона."""

    SYMBOL_WHITE = "\u2655"  # ♕
    SYMBOL_BLACK = "\u265B"  # ♛
    VALUE = 900
    NAME = "Q"

    _DIRECTIONS = [(-1, -1), (-1, 0), (-1, 1),
                   (0, -1),           (0, 1),
                   (1, -1),  (1, 0),  (1, 1)]

    def get_pseudo_legal_moves(self, board, row: int, col: int) -> list[tuple[int, int]]:
        return _slide(board, row, col, self._color, self._DIRECTIONS)


class Rook(Piece):
    """Тура. Ходить на будь-яку кількість клітин по горизонталі або вертикалі."""

    SYMBOL_WHITE = "\u2656"  # ♖
    SYMBOL_BLACK = "\u265C"  # ♜
    VALUE = 500
    NAME = "R"

    _DIRECTIONS = [(-1, 0), (1, 0), (0, -1), (0, 1)]

    def get_pseudo_legal_moves(self, board, row: int, col: int) -> list[tuple[int, int]]:
        return _slide(board, row, col, self._color, self._DIRECTIONS)


class Bishop(Piece):
    """Слон. Ходить діагонально на будь-яку кількість клітин."""

    SYMBOL_WHITE = "\u2657"  # ♗
    SYMBOL_BLACK = "\u265D"  # ♝
    VALUE = 330
    NAME = "B"

    _DIRECTIONS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    def get_pseudo_legal_moves(self, board, row: int, col: int) -> list[tuple[int, int]]:
        return _slide(board, row, col, self._color, self._DIRECTIONS)


class Knight(Piece):
    """Кінь. Ходить «літерою Г»."""

    SYMBOL_WHITE = "\u2658"  # ♘
    SYMBOL_BLACK = "\u265E"  # ♞
    VALUE = 320
    NAME = "N"

    _OFFSETS = [(-2, -1), (-2, 1), (-1, -2), (-1, 2),
                (1, -2),  (1, 2),  (2, -1),  (2, 1)]

    def get_pseudo_legal_moves(self, board, row: int, col: int) -> list[tuple[int, int]]:
        moves: list[tuple[int, int]] = []
        for dr, dc in self._OFFSETS:
            r, c = row + dr, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target = board.get_piece(r, c)
                if target is None or target.color != self._color:
                    moves.append((r, c))
        return moves


class Pawn(Piece):
    """
    Пішак. Найскладніша фігура за правилами:
        - ходить на 1 клітину вперед, із початкової позиції — на 2;
        - бʼє по діагоналі вперед;
        - підтримує взяття «на проході» (en passant);
        - перетворюється при досягненні останньої горизонталі.
    """

    SYMBOL_WHITE = "\u2659"  # ♙
    SYMBOL_BLACK = "\u265F"  # ♟
    VALUE = 100
    NAME = "P"

    def get_pseudo_legal_moves(self, board, row: int, col: int) -> list[tuple[int, int]]:
        moves: list[tuple[int, int]] = []
        # Білі рухаються «вгору» (зменшуючи номер ряду), чорні — «вниз».
        direction = -1 if self._color == WHITE else 1
        start_row = 6 if self._color == WHITE else 1

        # Хід на одну клітину вперед, якщо клітина вільна.
        one_ahead = row + direction
        if 0 <= one_ahead < 8 and board.get_piece(one_ahead, col) is None:
            moves.append((one_ahead, col))
            # Хід на дві клітини з початкової позиції.
            two_ahead = row + 2 * direction
            if row == start_row and board.get_piece(two_ahead, col) is None:
                moves.append((two_ahead, col))

        # Взяття по діагоналі.
        for dc in (-1, 1):
            r, c = row + direction, col + dc
            if 0 <= r < 8 and 0 <= c < 8:
                target = board.get_piece(r, c)
                if target is not None and target.color != self._color:
                    moves.append((r, c))
                # Взяття «на проході» (en passant) — обчислюється у GameState
                # за полем en_passant_target. Тут лише підказка:
                if (r, c) == board.en_passant_target:
                    moves.append((r, c))
        return moves


# Зручний словник для створення фігур за літерою.
PIECE_BY_LETTER = {
    "K": King, "Q": Queen, "R": Rook,
    "B": Bishop, "N": Knight, "P": Pawn
}


def piece_from_letter(letter: str, color: str) -> Piece:
    """Створює фігуру за її літерним позначенням ("K", "Q", "R", "B", "N", "P")."""
    cls = PIECE_BY_LETTER[letter.upper()]
    return cls(color)
