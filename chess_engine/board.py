"""
Модуль board.py
===============
Містить клас Board, який представляє стан шахової дошки 8х8.

Дошка зберігається як двовимірний список 8х8, де кожна клітина —
або None (порожня), або екземпляр Piece. Координати: (row, col), де
row=0 — верхній (8-й) ряд із точки зору білих, row=7 — нижній (1-й).
Стовпці: col=0 -> файл a, col=7 -> файл h.

Клас містить також службові поля для повноцінної підтримки правил:
    en_passant_target — клітина, доступна для взяття «на проході»;
    рокіровка та лічильники зберігаються у GameState (модуль game.py).
"""

from chess_engine.pieces import (
    Piece, King, Queen, Rook, Bishop, Knight, Pawn, WHITE, BLACK
)


class Board:
    """
    Шахова дошка 8х8 з фігурами.

    Атрибути:
        squares (list[list[Piece|None]]): двовимірний масив клітин;
        en_passant_target (tuple[int,int]|None): координата клітини,
            доступної для взяття «на проході»; None — якщо такої немає.
    """

    SIZE = 8

    def __init__(self) -> None:
        self.squares: list[list[Piece | None]] = [
            [None for _ in range(self.SIZE)] for _ in range(self.SIZE)
        ]
        self.en_passant_target: tuple[int, int] | None = None

    # --------------------- Базові операції ---------------------- #
    def get_piece(self, row: int, col: int) -> Piece | None:
        """Повертає фігуру в клітині (row, col) або None."""
        if 0 <= row < self.SIZE and 0 <= col < self.SIZE:
            return self.squares[row][col]
        return None

    def set_piece(self, row: int, col: int, piece: Piece | None) -> None:
        """Встановлює фігуру (або None) в клітину (row, col)."""
        if 0 <= row < self.SIZE and 0 <= col < self.SIZE:
            self.squares[row][col] = piece

    def clear(self) -> None:
        """Прибирає усі фігури з дошки."""
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                self.squares[r][c] = None
        self.en_passant_target = None

    # --------------------- Початкова розстановка --------------- #
    def setup_standard(self) -> None:
        """
        Розставляє фігури у стандартну початкову позицію.
        Білі займають ряди 6 (пішаки) і 7 (старші фігури),
        чорні — ряди 0 (старші) і 1 (пішаки).
        """
        self.clear()
        # Чорні (зверху).
        back_row_black = [Rook(BLACK), Knight(BLACK), Bishop(BLACK), Queen(BLACK),
                          King(BLACK), Bishop(BLACK), Knight(BLACK), Rook(BLACK)]
        for c, piece in enumerate(back_row_black):
            self.set_piece(0, c, piece)
            self.set_piece(1, c, Pawn(BLACK))
        # Білі (знизу).
        back_row_white = [Rook(WHITE), Knight(WHITE), Bishop(WHITE), Queen(WHITE),
                          King(WHITE), Bishop(WHITE), Knight(WHITE), Rook(WHITE)]
        for c, piece in enumerate(back_row_white):
            self.set_piece(7, c, piece)
            self.set_piece(6, c, Pawn(WHITE))

    # --------------------- Пошук фігур ------------------------- #
    def find_king(self, color: str) -> tuple[int, int] | None:
        """Шукає короля заданого кольору. Повертає координати або None."""
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                piece = self.squares[r][c]
                if isinstance(piece, King) and piece.color == color:
                    return (r, c)
        return None

    def all_pieces(self, color: str | None = None):
        """
        Генератор: повертає (row, col, piece) для усіх фігур.
        Якщо вказано колір — фільтрує лише фігури цього кольору.
        """
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                piece = self.squares[r][c]
                if piece is not None and (color is None or piece.color == color):
                    yield r, c, piece

    # --------------------- Копіювання -------------------------- #
    def copy(self) -> "Board":
        """
        Створює копію дошки. Фігури також копіюються (нові обʼєкти),
        щоб уникнути спільної мутації під час прорахунку ходів AI.
        """
        new_board = Board()
        for r in range(self.SIZE):
            for c in range(self.SIZE):
                piece = self.squares[r][c]
                if piece is not None:
                    # Створюємо новий обʼєкт того ж класу.
                    new_piece = piece.__class__(piece.color)
                    new_piece.has_moved = piece.has_moved
                    new_board.squares[r][c] = new_piece
        new_board.en_passant_target = self.en_passant_target
        return new_board

    # --------------------- Серіалізація ------------------------ #
    @staticmethod
    def square_name(row: int, col: int) -> str:
        """Перетворює (row, col) у шахову нотацію типу 'e4'."""
        files = "abcdefgh"
        return f"{files[col]}{8 - row}"

    @staticmethod
    def parse_square(name: str) -> tuple[int, int]:
        """Перетворює нотацію типу 'e4' у (row, col)."""
        files = "abcdefgh"
        col = files.index(name[0].lower())
        row = 8 - int(name[1])
        return row, col

    def to_text(self) -> str:
        """
        Повертає текстове представлення дошки (для збереження у файл).
        Формат: 8 рядків по 8 символів. Велика літера — біла фігура,
        мала — чорна, '.' — порожня клітина. У кінці може бути
        додатковий рядок із полем en passant.
        """
        lines = []
        for r in range(self.SIZE):
            row_chars = []
            for c in range(self.SIZE):
                piece = self.squares[r][c]
                if piece is None:
                    row_chars.append(".")
                else:
                    letter = piece.NAME
                    row_chars.append(letter if piece.color == WHITE else letter.lower())
            lines.append("".join(row_chars))
        if self.en_passant_target is not None:
            lines.append(f"ep={self.square_name(*self.en_passant_target)}")
        return "\n".join(lines)

    @classmethod
    def from_text(cls, text: str) -> "Board":
        """Відновлює дошку з текстового представлення."""
        board = cls()
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        # Перші 8 рядків — клітини.
        for r, line in enumerate(lines[:8]):
            for c, ch in enumerate(line[:8]):
                if ch == ".":
                    continue
                color = WHITE if ch.isupper() else BLACK
                from chess_engine.pieces import piece_from_letter
                board.set_piece(r, c, piece_from_letter(ch.upper(), color))
        # Додаткові рядки — параметри.
        for extra in lines[8:]:
            if extra.startswith("ep="):
                value = extra[3:]
                if value and value != "-":
                    board.en_passant_target = cls.parse_square(value)
        return board
