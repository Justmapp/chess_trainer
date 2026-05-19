"""
Модуль app.py
=============
Містить головний клас програми ChessApp — основне вікно tkinter, у якому
розташовані: шахова дошка (BoardWidget), бічна панель з меню та кнопками,
історія ходів та статус гри.

Підтримувані режими:
    * PvP (гравець проти гравця за одним екраном);
    * PvE (гравець проти комп'ютера);
    * Тренажер (вільна розстановка фігур, моделювання позицій).

Хід AI виконується в окремому потоці, щоб не «заморожувати» інтерфейс.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog

from chess_engine import (
    GameState, ChessAI, Board, Move,
    Piece, King, Queen, Rook, Bishop, Knight, Pawn,
    WHITE, BLACK, piece_from_letter
)
from gui.board_widget import BoardWidget
from gui import constants as C


# Шлях до папки збережень: <корінь проєкту>/saves
SAVES_DIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "saves"
))


# =====================================================================
#                        Головне вікно
# =====================================================================
class ChessApp(tk.Tk):
    """Головне вікно шахового тренажера."""

    # Можливі режими роботи.
    MODE_MENU = "menu"
    MODE_PVP = "pvp"
    MODE_PVE = "pve"
    MODE_TRAINER = "trainer"

    def __init__(self) -> None:
        super().__init__()
        self.title("Шаховий тренажер")
        self.resizable(False, False)
        try:
            # Створимо теку для збережень, якщо ще не існує.
            os.makedirs(SAVES_DIR, exist_ok=True)
        except OSError:
            pass

        # Стан програми.
        self.mode: str = self.MODE_MENU
        self.game: GameState = GameState()
        self.ai: ChessAI = ChessAI(depth=C.DEFAULT_AI_DEPTH)
        self.human_color: str = WHITE
        self.selected_square: tuple[int, int] | None = None
        self.legal_moves_cache: list[Move] = []
        # У режимі тренажера — обраний тип фігури для розставляння.
        self.placement_piece: tuple[str, str] | None = None  # ("W","K") тощо
        # Прапорець, чи AI зараз думає.
        self.ai_thinking: bool = False

        # Будуємо інтерфейс.
        self._build_menu_screen()

    # ===========================================================
    #                    Стартове меню
    # ===========================================================
    def _build_menu_screen(self) -> None:
        """Стартове вікно з вибором режиму."""
        self._clear_window()
        self.mode = self.MODE_MENU
        self.geometry("500x550")

        title = tk.Label(self, text="ШАХОВИЙ ТРЕНАЖЕР",
                         font=("Arial", 22, "bold"), pady=20)
        title.pack()
        subtitle = tk.Label(self, text="Курсова робота з ОП",
                            font=("Arial", 10, "italic"), fg="#666")
        subtitle.pack(pady=(0, 30))

        button_style = {"font": ("Arial", 13), "width": 50, "pady": 8}

        tk.Button(self, text="Гра двох гравців (PvP)",
                  command=self._start_pvp, **button_style).pack(pady=4)

        tk.Button(self, text="Гра проти комп'ютера (PvE)",
                  command=self._start_pve_dialog, **button_style).pack(pady=4)

        tk.Button(self, text="Режим тренажера (вільна розстановка)",
                  command=self._start_trainer, **button_style).pack(pady=4)

        tk.Button(self, text="Завантажити збережену партію",
                  command=self._load_game_dialog, **button_style).pack(pady=4)

        tk.Button(self, text="Вийти", command=self.destroy,
                  **button_style).pack(pady=4)

        info = tk.Label(self,
                        text="© 2026 Гриценко Р.О., ІП-55\nІПІ ФІОТ, КПІ ім. Ігоря Сікорського",
                        font=("Arial", 9), fg="#888", pady=20)
        info.pack(side=tk.BOTTOM)

    # ===========================================================
    #                Запуск різних режимів
    # ===========================================================
    def _start_pvp(self) -> None:
        self.mode = self.MODE_PVP
        self.game = GameState()
        self.human_color = WHITE
        self._build_game_screen()

    def _start_pve_dialog(self) -> None:
        """Діалог вибору параметрів PvE-режиму."""
        dialog = tk.Toplevel(self)
        dialog.title("Налаштування гри з комп'ютером")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.update_idletasks()
        w = dialog.winfo_width()
        h = dialog.winfo_height()
        x = self.winfo_x() + (self.winfo_width() // 2) - (w // 2)
        y = self.winfo_y() + (self.winfo_height() // 2) - (h // 2)
        dialog.geometry(f"+{x}+{y}")

        tk.Label(dialog, text="Грати кольором:",
                 font=("Arial", 11)).grid(row=0, column=0, padx=10, pady=8,
                                          sticky="w")
        color_var = tk.StringVar(value=WHITE)
        ttk.Radiobutton(dialog, text="Білі", variable=color_var,
                        value=WHITE).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(dialog, text="Чорні", variable=color_var,
                        value=BLACK).grid(row=0, column=2, sticky="w")

        tk.Label(dialog, text="Складність (глибина):",
                 font=("Arial", 11)).grid(row=1, column=0, padx=10, pady=8,
                                          sticky="w")
        depth_var = tk.StringVar(value=str(C.DEFAULT_AI_DEPTH))
        ttk.Spinbox(dialog, from_=C.MIN_AI_DEPTH, to=C.MAX_AI_DEPTH,
                    textvariable=depth_var, width=5).grid(row=1, column=1,
                                                           columnspan=2,
                                                           sticky="w")

        def confirm():
            raw = depth_var.get().strip()
            if not raw.lstrip('-').isdigit():
                messagebox.showerror("Помилка",
                                     f"Введіть ціле число від {C.MIN_AI_DEPTH} до {C.MAX_AI_DEPTH}.",
                                     parent=dialog)
                return
            depth = int(raw)
            if not (C.MIN_AI_DEPTH <= depth <= C.MAX_AI_DEPTH):
                messagebox.showerror("Помилка",
                                     f"Складність має бути від {C.MIN_AI_DEPTH} до {C.MAX_AI_DEPTH}.",
                                     parent=dialog)
                return
            self.human_color = color_var.get()
            self.ai = ChessAI(depth=depth)
            dialog.destroy()
            self._start_pve()

        tk.Button(dialog, text="Почати гру", command=confirm,
                  font=("Arial", 11), width=15).grid(row=2, column=0,
                                                     columnspan=3, pady=12)

    def _start_pve(self) -> None:
        self.mode = self.MODE_PVE
        self.game = GameState()
        self._build_game_screen()
        # Якщо людина грає чорними — AI робить перший хід.
        if self.human_color == BLACK:
            self.after(300, self._make_ai_move)

    def _start_trainer(self) -> None:
        self.mode = self.MODE_TRAINER
        self.game = GameState()
        # У тренажері починаємо з чистої дошки.
        self.game.board.clear()
        self.placement_piece = None
        self._build_trainer_screen()

    def _load_game_dialog(self) -> None:
        path = filedialog.askopenfilename(
            initialdir=SAVES_DIR,
            title="Виберіть файл збереження",
            filetypes=[("Файли збереження", "*.txt"), ("Усі файли", "*.*")]
        )
        if not path:
            return
        if not path.lower().endswith(".txt"):
            messagebox.showerror("Невірний тип файлу",
                                 "Можна завантажувати лише файли формату .txt")
            return
        try:
            self.game = GameState.load_from_file(path)
        except Exception:
            messagebox.showerror("Пошкоджений файл",
                                 "Файл має невірний формат або пошкоджений.\n"
                                 "Завантажте коректний файл збереження.")
            return
        self.mode = self.MODE_PVP   # за замовч. перейти у PvP
        self.human_color = WHITE
        self._build_game_screen()

    # ===========================================================
    #                Екран ігрового режиму
    # ===========================================================
    def _build_game_screen(self) -> None:
        """Створює віджети для ігрового режиму PvP/PvE."""
        self._clear_window()
        size_w = (C.BOARD_PIXEL_SIZE + 2 * C.COORD_MARGIN
                  + C.SIDE_PANEL_WIDTH + 20)
        size_h = C.BOARD_PIXEL_SIZE + 2 * C.COORD_MARGIN + 20
        self.geometry(f"{size_w}x{size_h}")

        # Дошка ліворуч.
        self.board_widget = BoardWidget(self,
                                        on_square_click=self._on_board_click)
        self.board_widget.pack(side=tk.LEFT, padx=10, pady=10)
        self.board_widget.set_board(self.game.board)
        # Якщо людина чорними — перевернути.
        self.board_widget.set_flipped(self.mode == self.MODE_PVE
                                       and self.human_color == BLACK)

        # Бічна панель праворуч.
        side = tk.Frame(self, width=C.SIDE_PANEL_WIDTH)
        side.pack(side=tk.RIGHT, fill=tk.Y, padx=8, pady=10)
        side.pack_propagate(False)

        title_text = ("Гра двох гравців" if self.mode == self.MODE_PVP
                      else "Гра проти комп'ютера")
        tk.Label(side, text=title_text, font=C.TITLE_FONT).pack(pady=4)

        self.status_var = tk.StringVar(value="Хід білих")
        tk.Label(side, textvariable=self.status_var,
                 font=("Arial", 11, "bold")).pack(pady=2)

        # Список ходів із прокруткою.
        history_frame = tk.LabelFrame(side, text="Історія ходів",
                                      font=("Arial", 10))
        history_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        scrollbar = tk.Scrollbar(history_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.history_list = tk.Listbox(history_frame,
                                        yscrollcommand=scrollbar.set,
                                        font=("Courier New", 10))
        self.history_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.history_list.yview)

        # Кнопки керування.
        btn_frame = tk.Frame(side)
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text="Скасувати хід",
                  command=self._undo_move, width=14).grid(row=0, column=0,
                                                          padx=2, pady=2)
        tk.Button(btn_frame, text="Перевернути",
                  command=self._flip_board, width=14).grid(row=0, column=1,
                                                            padx=2, pady=2)
        tk.Button(btn_frame, text="Зберегти",
                  command=self._save_game, width=14).grid(row=1, column=0,
                                                          padx=2, pady=2)
        tk.Button(btn_frame, text="Нова гра",
                  command=self._new_game, width=14).grid(row=1, column=1,
                                                         padx=2, pady=2)
        tk.Button(btn_frame, text="Головне меню",
                  command=self._confirm_go_to_menu, width=30).grid(row=2,
                                                                    column=0,
                                                                    columnspan=2,
                                                                    padx=2,
                                                                    pady=2)

        self._refresh_history()
        self._update_status()

    # ===========================================================
    #                Екран режиму тренажера
    # ===========================================================
    def _build_trainer_screen(self) -> None:
        """Створює віджети для режиму тренажера (вільної розстановки)."""
        self._clear_window()
        size_w = (C.BOARD_PIXEL_SIZE + 2 * C.COORD_MARGIN
                  + C.SIDE_PANEL_WIDTH + 20)
        size_h = C.BOARD_PIXEL_SIZE + 2 * C.COORD_MARGIN + 20
        self.geometry(f"{size_w}x{size_h}")

        self.board_widget = BoardWidget(self,
                                        on_square_click=self._on_trainer_click)
        self.board_widget.pack(side=tk.LEFT, padx=10, pady=10)
        self.board_widget.set_board(self.game.board)
        self.board_widget.set_flipped(False)

        side = tk.Frame(self, width=C.SIDE_PANEL_WIDTH)
        side.pack(side=tk.RIGHT, fill=tk.Y, padx=8, pady=10)
        side.pack_propagate(False)

        tk.Label(side, text="Тренажер позицій",
                 font=C.TITLE_FONT).pack(pady=4)
        tk.Label(side, text="Виберіть фігуру і клацайте\nпо клітинах дошки",
                 font=("Arial", 10), fg="#444").pack(pady=2)

        # Палітра фігур (білі та чорні).
        for color_label, color_code, color_letter in [
            ("Білі", WHITE, "W"), ("Чорні", BLACK, "B"),
        ]:
            tk.Label(side, text=color_label,
                     font=("Arial", 11, "bold")).pack(pady=(8, 2))
            row_frame = tk.Frame(side)
            row_frame.pack()
            for letter in ["K", "Q", "R", "B", "N", "P"]:
                piece = piece_from_letter(letter, color_code)
                btn = tk.Button(row_frame, text=piece.symbol,
                                font=("DejaVu Sans", 22),
                                fg="white" if color_code == WHITE else "black",
                                bg="#666" if color_code == WHITE else "#DDD",
                                width=2,
                                command=lambda l=letter, c=color_letter:
                                    self._select_placement(c, l))
                btn.pack(side=tk.LEFT, padx=1, pady=1)

        # Кнопка «прибрати».
        tk.Button(side, text="🗑 Очистити клітину",
                  command=lambda: self._select_placement(None, None),
                  font=("Arial", 10), width=22).pack(pady=8)

        self.placement_var = tk.StringVar(value="Обрано: нічого")
        tk.Label(side, textvariable=self.placement_var,
                 font=("Arial", 10), fg="#005599").pack(pady=2)

        # Кнопки операцій.
        sep = tk.Frame(side, height=2, bg="#888")
        sep.pack(fill=tk.X, pady=8)

        tk.Label(side, text="Чий хід:",
                 font=("Arial", 10)).pack(pady=(2, 0))
        self.trainer_turn_var = tk.StringVar(value=WHITE)
        ttk.Radiobutton(side, text="Білі", variable=self.trainer_turn_var,
                        value=WHITE).pack(anchor="w", padx=20)
        ttk.Radiobutton(side, text="Чорні", variable=self.trainer_turn_var,
                        value=BLACK).pack(anchor="w", padx=20)

        tk.Button(side, text="Очистити дошку",
                  command=self._trainer_clear_board, width=22).pack(pady=2)
        tk.Button(side, text="Стандартна розстановка",
                  command=self._trainer_setup_standard, width=22).pack(pady=2)
        tk.Button(side, text="▶ Грати з цієї позиції",
                  command=self._trainer_play_from_here,
                  font=("Arial", 10, "bold"),
                  bg="#90C695", width=22).pack(pady=8)
        tk.Button(side, text="Зберегти позицію",
                  command=self._save_game, width=22).pack(pady=2)
        tk.Button(side, text="Завантажити позицію",
                  command=self._load_game_dialog, width=22).pack(pady=2)
        tk.Button(side, text="Головне меню",
                  command=self._build_menu_screen, width=22).pack(pady=8)

    # ===========================================================
    #              Обробники подій (ігровий режим)
    # ===========================================================
    def _on_board_click(self, row: int, col: int) -> None:
        """Клік по дошці у режимі гри."""
        if self.game.is_game_over():
            return
        if self.ai_thinking:
            return
        # У PvE — не дозволяємо ходити, поки чужий хід.
        if (self.mode == self.MODE_PVE
                and self.game.current_player != self.human_color):
            return

        clicked_piece = self.game.board.get_piece(row, col)

        if self.selected_square is None:
            # Першиx клік: обрати свою фігуру.
            if (clicked_piece is not None
                    and clicked_piece.color == self.game.current_player):
                self._select_square(row, col)
        else:
            # Другий клік: спробувати зробити хід або переобрати.
            target_move = next(
                (m for m in self.legal_moves_cache if m.to_pos == (row, col)),
                None
            )
            if target_move is not None:
                self._execute_move_with_promotion(target_move)
            else:
                # Якщо клікнули на свою іншу фігуру — переобрати.
                if (clicked_piece is not None
                        and clicked_piece.color == self.game.current_player):
                    self._select_square(row, col)
                else:
                    self._deselect()

    def _select_square(self, row: int, col: int) -> None:
        self.selected_square = (row, col)
        all_legal = self.game.get_legal_moves()
        self.legal_moves_cache = [m for m in all_legal if m.from_pos == (row, col)]
        # Підсвітити: обрану клітину + цілі ходів.
        highlights = {(row, col): C.SELECTED_COLOR}
        for m in self.legal_moves_cache:
            highlights[m.to_pos] = C.LEGAL_MOVE_COLOR
        self.board_widget.set_highlights(highlights)

    def _deselect(self) -> None:
        self.selected_square = None
        self.legal_moves_cache = []
        self.board_widget.clear_highlights()

    def _execute_move_with_promotion(self, move: Move) -> None:
        """Якщо хід — перетворення, питаємо у користувача фігуру."""
        if move.promotion is not None:
            # Знайти усі варіанти перетворення з тим самим від/до.
            promo_moves = [m for m in self.legal_moves_cache
                           if m.from_pos == move.from_pos
                           and m.to_pos == move.to_pos
                           and m.promotion is not None]
            chosen = self._ask_promotion()
            move = next((m for m in promo_moves if m.promotion == chosen),
                        promo_moves[0])
        self._execute_move(move)

    def _ask_promotion(self) -> str:
        """Просте діалогове вікно для вибору фігури перетворення."""
        dialog = tk.Toplevel(self)
        dialog.title("Перетворення пішака")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        result = {"piece": "Q"}
        tk.Label(dialog, text="Оберіть фігуру для перетворення:",
                 font=("Arial", 11), pady=8).pack()
        frame = tk.Frame(dialog)
        frame.pack(pady=8)

        def choose(letter: str):
            result["piece"] = letter
            dialog.destroy()

        for letter, name in [("Q", "Ферзь"), ("R", "Тура"),
                              ("B", "Слон"), ("N", "Кінь")]:
            tk.Button(frame, text=name, width=8, font=("Arial", 10),
                      command=lambda l=letter: choose(l)).pack(side=tk.LEFT,
                                                                padx=3)

        self.wait_window(dialog)
        return result["piece"]

    def _execute_move(self, move: Move) -> None:
        """Зробити хід, оновити інтерфейс і, якщо треба, запустити AI."""
        self.game.make_move(move)
        self._deselect()
        self.board_widget.set_last_move([move.from_pos, move.to_pos])
        self._refresh_history()
        self._update_status()
        self.board_widget.redraw()

        if self.game.is_game_over():
            self._show_game_over()
            return

        # Якщо PvE і тепер хід AI — запустити його.
        if (self.mode == self.MODE_PVE
                and self.game.current_player != self.human_color):
            self.after(150, self._make_ai_move)

    def _make_ai_move(self) -> None:
        """Запускає AI у фоновому потоці, щоб не блокувати GUI."""
        if self.game.is_game_over() or self.ai_thinking:
            return
        self.ai_thinking = True
        self.status_var.set("Комп'ютер думає...")

        def worker():
            move = self.ai.choose_best_move(self.game)
            # Повертаємось у головний потік для оновлення GUI.
            self.after(0, lambda m=move: self._apply_ai_move(m))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_ai_move(self, move: Move | None) -> None:
        self.ai_thinking = False
        if move is None:
            self._update_status()
            return
        self.game.make_move(move)
        self.board_widget.set_last_move([move.from_pos, move.to_pos])
        self._refresh_history()
        self._update_status()
        self.board_widget.redraw()
        if self.game.is_game_over():
            self._show_game_over()

    def _undo_move(self) -> None:
        if self.ai_thinking:
            return
        # У PvE відкочуємо два напівходи (свій + AI), якщо можливо.
        steps = 2 if self.mode == self.MODE_PVE else 1
        for _ in range(steps):
            if not self.game.undo_move():
                break
        self._deselect()
        last = self.game.move_history[-1] if self.game.move_history else None
        self.board_widget.set_last_move(
            [last.from_pos, last.to_pos] if last else []
        )
        self._refresh_history()
        self._update_status()
        self.board_widget.redraw()
        if (self.mode == self.MODE_PVE
                and not self.game.is_game_over()
                and self.game.current_player != self.human_color):
            self.after(300, self._make_ai_move)

    def _flip_board(self) -> None:
        self.board_widget.set_flipped(not self.board_widget._flipped)

    def _confirm_go_to_menu(self) -> None:
        if self.game.move_history:
            if not messagebox.askyesno("Головне меню",
                                       "Повернутись до головного меню?\n"
                                       "Незбережений прогрес буде втрачено."):
                return
        self._build_menu_screen()

    def _new_game(self) -> None:
        if not messagebox.askyesno("Нова гра",
                                    "Розпочати нову партію?"):
            return
        self.game = GameState()
        self._deselect()
        self.board_widget.set_board(self.game.board)
        self.board_widget.set_last_move([])
        self.board_widget.set_check_square(None)
        self._refresh_history()
        self._update_status()
        if (self.mode == self.MODE_PVE
                and self.human_color == BLACK):
            self.after(300, self._make_ai_move)

    def _save_game(self) -> None:
        path = filedialog.asksaveasfilename(
            initialdir=SAVES_DIR,
            title="Зберегти партію",
            defaultextension=".txt",
            filetypes=[("Файли збереження", "*.txt")]
        )
        if not path:
            return
        try:
            if self.mode == self.MODE_TRAINER:
                if (self.game.board.find_king(WHITE) is None
                        or self.game.board.find_king(BLACK) is None):
                    messagebox.showerror("Помилка",
                                         "Для збереження на дошці мають бути обидва королі.")
                    return
                start_color = self.trainer_turn_var.get()
                opponent_color = BLACK if start_color == WHITE else WHITE
                if self.game.is_in_check(opponent_color):
                    messagebox.showerror("Помилка",
                                         "Позиція некоректна: король сторони, "
                                         "що не ходить, стоїть під шахом.")
                    return
                self.game.current_player = self.trainer_turn_var.get()
            self.game.save_to_file(path)
            messagebox.showinfo("Збережено", f"Партію збережено у\n{path}")
        except Exception as e:
            messagebox.showerror("Помилка", str(e))

    # ===========================================================
    #              Обробники подій (тренажер)
    # ===========================================================
    def _select_placement(self, color_letter: str | None,
                          piece_letter: str | None) -> None:
        """Обрати тип фігури для розставляння (або 'нічого' для очищення)."""
        if color_letter is None or piece_letter is None:
            self.placement_piece = None
            self.placement_var.set("Обрано: ✖ очистити клітину")
        else:
            self.placement_piece = (color_letter, piece_letter)
            color_name = "Білі" if color_letter == "W" else "Чорні"
            piece_name = {"K": "Король", "Q": "Ферзь", "R": "Тура",
                           "B": "Слон", "N": "Кінь", "P": "Пішак"}[piece_letter]
            self.placement_var.set(f"Обрано: {color_name} {piece_name}")

    def _on_trainer_click(self, row: int, col: int) -> None:
        """Клік по дошці у тренажері: ставимо/прибираємо фігуру."""
        if self.placement_piece is None:
            # «Очистити» — просто прибрати фігуру.
            self.game.board.set_piece(row, col, None)
        else:
            color_letter, piece_letter = self.placement_piece
            color = WHITE if color_letter == "W" else BLACK
            # Заборона: тільки один король кожного кольору.
            if piece_letter == "K":
                king_pos = self.game.board.find_king(color)
                if king_pos is not None and king_pos != (row, col):
                    self.game.board.set_piece(king_pos[0], king_pos[1], None)
                    # Заборона: два королі не можуть стояти поруч.
            if piece_letter == "K":
                enemy_color = BLACK if color == WHITE else WHITE
                enemy_king_pos = self.game.board.find_king(enemy_color)
                if (enemy_king_pos is not None
                        and abs(enemy_king_pos[0] - row) <= 1
                        and abs(enemy_king_pos[1] - col) <= 1):
                    messagebox.showwarning("Недопустима розстановка",
                                                   "Королі не можуть стояти поруч.")
                    return
            # Заборона: пішак не може стояти на крайніх горизонталях.
            if piece_letter == "P" and (row == 0 or row == 7):
                messagebox.showwarning("Недопустима розстановка",
                                        "Пішак не може стояти на 1-й або 8-й горизонталі.")
                return
            self.game.board.set_piece(row, col,
                                      piece_from_letter(piece_letter, color))
        self.board_widget.redraw()

    def _trainer_clear_board(self) -> None:
        self.game.board.clear()
        self.board_widget.redraw()

    def _trainer_setup_standard(self) -> None:
        self.game.board.setup_standard()
        self.board_widget.redraw()

    def _trainer_play_from_here(self) -> None:
        """Перейти з тренажера у режим гри з поточною позицією."""
        # Перевірка коректності: мають бути два королі.
        if (self.game.board.find_king(WHITE) is None
                or self.game.board.find_king(BLACK) is None):
            messagebox.showerror("Помилка",
                                  "Для початку гри на дошці мають бути обидва королі.")
            return
            # Перевірка: король сторони, що НЕ ходить, не може стояти під шахом.
        start_color = self.trainer_turn_var.get()
        opponent_color = BLACK if start_color == WHITE else WHITE
        if self.game.is_in_check(opponent_color):
            messagebox.showerror("Помилка",
                                    "Позиція некоректна: король сторони, "
                                    "що не ходить, стоїть під шахом.")
            return
        # Створюємо новий GameState із поточної дошки.
        new_game = GameState()
        new_game.board = self.game.board.copy()
        new_game.current_player = self.trainer_turn_var.get()
        new_game.move_history = []
        new_game.halfmove_clock = 0
        new_game.fullmove_number = 1
        new_game._position_counts = {}
        # Скинути прапорці has_moved для коректних рокіровок з нової позиції.
        new_game._recompute_castling_rights()
        new_game._position_counts[new_game._position_key()] = 1
        # Запитати режим: PvP чи PvE?
        ans = messagebox.askyesnocancel("Режим гри",
                                         "Грати проти комп'ютера?\n"
                                         "(Так — PvE, Ні — два гравці, "
                                         "Скасувати — повернутися)")
        if ans is None:
            return
        self.game = new_game
        if ans:
            self.mode = self.MODE_PVE
            self.human_color = new_game.current_player
            self.ai = ChessAI(depth=C.DEFAULT_AI_DEPTH)
        else:
            self.mode = self.MODE_PVP
            self.human_color = WHITE
        self._build_game_screen()

    # ===========================================================
    #                     Допоміжні методи
    # ===========================================================
    def _refresh_history(self) -> None:
        if not hasattr(self, "history_list"):
            return
        self.history_list.delete(0, tk.END)
        # Виводимо парами «N. білі чорні».
        moves = [m.to_algebraic() for m in self.game.move_history]
        for i in range(0, len(moves), 2):
            num = i // 2 + 1
            white_mv = moves[i]
            black_mv = moves[i + 1] if i + 1 < len(moves) else ""
            line = f"{num:>3}. {white_mv:<8} {black_mv}"
            self.history_list.insert(tk.END, line)
        self.history_list.see(tk.END)

    def _update_status(self) -> None:
        if not hasattr(self, "status_var"):
            return
        if self.game.is_game_over():
            self.status_var.set(self.game.get_result())
            self.board_widget.set_check_square(None)
            return
        turn = "Хід білих" if self.game.current_player == WHITE else "Хід чорних"
        if self.game.is_in_check(self.game.current_player):
            turn += "  ⚠ ШАХ!"
            king_sq = self.game.board.find_king(self.game.current_player)
            self.board_widget.set_check_square(king_sq)
        else:
            self.board_widget.set_check_square(None)
        self.status_var.set(turn)

    def _show_game_over(self) -> None:
        messagebox.showinfo("Партія завершена", self.game.get_result())

    def _clear_window(self) -> None:
        for widget in self.winfo_children():
            widget.destroy()
