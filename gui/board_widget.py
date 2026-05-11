"""
Модуль board_widget.py
======================
Містить клас BoardWidget — графічний компонент tkinter, що малює шахову
дошку, фігури та обробляє клацання миші.

Логіка не залежить від решти GUI: віджет лише сповіщає про клацнуту клітину
через колбек on_square_click.
"""

import tkinter as tk

from chess_engine.pieces import (
    Piece, King, Queen, Rook, Bishop, Knight, Pawn, WHITE, BLACK
)
from chess_engine.board import Board
from gui import constants as C


class BoardWidget(tk.Canvas):
    """
    Канва, що малює шахову дошку 8x8 та обробляє клацання користувача.

    Параметри ініціалізації:
        master: батьківський віджет;
        on_square_click: функція-колбек, що викликається з аргументами
            (row, col) при клацанні на клітині.
    """

    def __init__(self, master, on_square_click=None) -> None:
        # Загальний розмір канви: дошка + поля для координат.
        size = C.BOARD_PIXEL_SIZE + 2 * C.COORD_MARGIN
        super().__init__(master, width=size, height=size,
                         highlightthickness=0, bg="#3A2A1A")
        self._on_square_click = on_square_click
        self._board: Board | None = None
        self._flipped = False                 # перевертати чи ні дошку
        self._highlights: dict[tuple[int, int], str] = {}
        self._last_move_squares: list[tuple[int, int]] = []
        self._check_square: tuple[int, int] | None = None
        self.bind("<Button-1>", self._handle_click)

    # ------------------- Публічний API ----------------- #
    def set_board(self, board: Board) -> None:
        """Прив’язати об’єкт Board, який буде відображатися."""
        self._board = board
        self.redraw()

    def set_flipped(self, flipped: bool) -> None:
        """Перевернути дошку (для гри чорними)."""
        self._flipped = flipped
        self.redraw()

    def set_highlights(self, squares: dict[tuple[int, int], str]) -> None:
        """Встановити словник {клітина: колір} для підсвічування."""
        self._highlights = dict(squares)
        self.redraw()

    def clear_highlights(self) -> None:
        self._highlights.clear()
        self.redraw()

    def set_last_move(self, squares: list[tuple[int, int]]) -> None:
        """Підсвітити клітини останнього ходу (зазвичай from + to)."""
        self._last_move_squares = list(squares)
        self.redraw()

    def set_check_square(self, square: tuple[int, int] | None) -> None:
        """Підсвітити клітину короля, що під шахом."""
        self._check_square = square
        self.redraw()

    # ------------------- Малювання --------------------- #
    def redraw(self) -> None:
        """Повне перемалювання дошки і фігур."""
        self.delete("all")
        if self._board is None:
            return
        self._draw_squares()
        self._draw_coordinates()
        self._draw_pieces()

    def _to_visual(self, row: int, col: int) -> tuple[int, int]:
        """Перетворює (логічний row, col) у (vrow, vcol) з урахуванням повороту."""
        if self._flipped:
            return 7 - row, 7 - col
        return row, col

    def _from_visual(self, vrow: int, vcol: int) -> tuple[int, int]:
        """Зворотне перетворення."""
        if self._flipped:
            return 7 - vrow, 7 - vcol
        return vrow, vcol

    def _square_pixel(self, vrow: int, vcol: int) -> tuple[int, int]:
        """Координати лівого верхнього кута клітини у пікселях."""
        x = C.COORD_MARGIN + vcol * C.SQUARE_SIZE
        y = C.COORD_MARGIN + vrow * C.SQUARE_SIZE
        return x, y

    def _draw_squares(self) -> None:
        for row in range(8):
            for col in range(8):
                vrow, vcol = self._to_visual(row, col)
                x, y = self._square_pixel(vrow, vcol)
                base_color = (C.LIGHT_SQUARE_COLOR if (row + col) % 2 == 0
                              else C.DARK_SQUARE_COLOR)
                # Підсвічування.
                fill = base_color
                if (row, col) in self._last_move_squares:
                    fill = C.LAST_MOVE_COLOR
                if self._check_square == (row, col):
                    fill = C.CHECK_COLOR
                if (row, col) in self._highlights:
                    fill = self._highlights[(row, col)]
                self.create_rectangle(x, y, x + C.SQUARE_SIZE,
                                       y + C.SQUARE_SIZE,
                                       fill=fill, outline="")

    def _draw_coordinates(self) -> None:
        files = "abcdefgh"
        ranks = "87654321"
        if self._flipped:
            files = files[::-1]
            ranks = ranks[::-1]
        # Літери знизу та зверху.
        for vcol, letter in enumerate(files):
            x = C.COORD_MARGIN + vcol * C.SQUARE_SIZE + C.SQUARE_SIZE // 2
            self.create_text(x, C.COORD_MARGIN // 2, text=letter,
                             fill="#F0D9B5", font=C.COORD_FONT)
            self.create_text(x, C.COORD_MARGIN + C.BOARD_PIXEL_SIZE
                             + C.COORD_MARGIN // 2,
                             text=letter, fill="#F0D9B5", font=C.COORD_FONT)
        # Цифри ліворуч та праворуч.
        for vrow, digit in enumerate(ranks):
            y = C.COORD_MARGIN + vrow * C.SQUARE_SIZE + C.SQUARE_SIZE // 2
            self.create_text(C.COORD_MARGIN // 2, y, text=digit,
                             fill="#F0D9B5", font=C.COORD_FONT)
            self.create_text(C.COORD_MARGIN + C.BOARD_PIXEL_SIZE
                             + C.COORD_MARGIN // 2, y,
                             text=digit, fill="#F0D9B5", font=C.COORD_FONT)

    def _draw_pieces(self) -> None:
        if self._board is None:
            return
        for r in range(8):
            for c in range(8):
                piece = self._board.get_piece(r, c)
                if piece is None:
                    continue
                vrow, vcol = self._to_visual(r, c)
                x, y = self._square_pixel(vrow, vcol)
                cx = x + C.SQUARE_SIZE // 2
                cy = y + C.SQUARE_SIZE // 2
                fill = (C.WHITE_PIECE_COLOR if piece.color == WHITE
                        else C.BLACK_PIECE_COLOR)
                outline = (C.WHITE_PIECE_OUTLINE if piece.color == WHITE
                           else C.BLACK_PIECE_OUTLINE)
                # Малюємо тінь під фігурою для контрасту.
                self.create_text(cx + 1, cy + 2, text=piece.symbol,
                                 font=C.PIECE_FONT, fill="#222")
                # Сама фігура.
                self.create_text(cx, cy, text=piece.symbol,
                                 font=C.PIECE_FONT, fill=fill)
                # Контур (через двократне малювання — простий ефект).
                if piece.color == WHITE:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        self.create_text(cx + dx, cy + dy, text=piece.symbol,
                                         font=C.PIECE_FONT, fill=outline)
                    self.create_text(cx, cy, text=piece.symbol,
                                     font=C.PIECE_FONT, fill=fill)

    # --------------- Обробка кліків -------------------- #
    def _handle_click(self, event) -> None:
        """Перетворює координати миші на (row, col) і викликає колбек."""
        if self._on_square_click is None:
            return
        x, y = event.x - C.COORD_MARGIN, event.y - C.COORD_MARGIN
        if x < 0 or y < 0 or x >= C.BOARD_PIXEL_SIZE or y >= C.BOARD_PIXEL_SIZE:
            return
        vcol = x // C.SQUARE_SIZE
        vrow = y // C.SQUARE_SIZE
        row, col = self._from_visual(vrow, vcol)
        self._on_square_click(row, col)
