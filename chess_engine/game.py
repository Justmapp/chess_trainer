"""
Модуль game.py
==============
Містить клас GameState — головний клас, який керує перебігом шахової
партії: зберігає поточний стан дошки, чий хід, історію, права на
рокіровку, дотримує правила шахів (шах, мат, пат, нічия за повторенням
та правилом 50-ти ходів).

Реалізовано:
    * генерація легальних ходів (з врахуванням шахів власному королю);
    * виконання ходу (make_move) з оновленням усіх полів;
    * відкат ходу (undo_move) — критично важливо для AI;
    * перевірка шаху, мату, пату, недостатності матеріалу;
    * рокіровка (коротка та довга);
    * взяття «на проході»;
    * перетворення пішака.
"""

from chess_engine.board import Board
from chess_engine.move import Move
from chess_engine.pieces import (
    Piece, King, Queen, Rook, Bishop, Knight, Pawn,
    WHITE, BLACK, piece_from_letter
)


class GameState:
    """
    Поточний стан шахової партії.

    Атрибути:
        board (Board): дошка із фігурами;
        current_player (str): колір гравця, чий зараз хід;
        move_history (list[Move]): історія усіх зроблених ходів;
        castling_rights (dict): права на рокіровку для обох сторін;
        halfmove_clock (int): лічильник напівходів без взять/ходів пішаком
                              (для правила 50 ходів);
        fullmove_number (int): порядковий номер ходу (інкрементується
                               після ходу чорних).
    """

    def __init__(self) -> None:
        self.board = Board()
        self.board.setup_standard()
        self.current_player = WHITE
        self.move_history: list[Move] = []
        # Права на рокіровку для кожної сторони.
        self.castling_rights = {
            WHITE: {"kingside": True, "queenside": True},
            BLACK: {"kingside": True, "queenside": True},
        }
        self.halfmove_clock = 0
        self.fullmove_number = 1
        # Кеш-словник для виявлення повторень позицій (3-кратна нічия).
        self._position_counts: dict[str, int] = {}

    # ====================================================================
    #              Генерація і перевірка легальних ходів
    # ====================================================================

    def get_legal_moves(self, color: str | None = None) -> list[Move]:
        """
        Повертає список усіх легальних ходів для гравця заданого кольору.
        Якщо color не вказано — для поточного гравця.

        Алгоритм:
            1) для кожної своєї фігури отримати список псевдо-легальних ходів;
            2) додати спеціальні ходи (рокіровка, перетворення);
            3) відсіяти ходи, після яких власний король залишається під шахом.
        """
        if color is None:
            color = self.current_player

        legal_moves: list[Move] = []

        for r, c, piece in list(self.board.all_pieces(color)):
            for to_r, to_c in piece.get_pseudo_legal_moves(self.board, r, c):
                target = self.board.get_piece(to_r, to_c)

                # --- Перетворення пішака ---
                if isinstance(piece, Pawn) and (to_r == 0 or to_r == 7):
                    for promo in ("Q", "R", "B", "N"):
                        legal_moves.append(Move(
                            (r, c), (to_r, to_c), piece, target,
                            promotion=promo
                        ))
                    continue

                # --- Взяття «на проході» ---
                is_ep = (isinstance(piece, Pawn)
                         and (to_r, to_c) == self.board.en_passant_target
                         and target is None)
                if is_ep:
                    # «Захоплена» фігура знаходиться на полі поруч.
                    captured_pawn = self.board.get_piece(r, to_c)
                    legal_moves.append(Move(
                        (r, c), (to_r, to_c), piece, captured_pawn,
                        is_en_passant=True
                    ))
                else:
                    legal_moves.append(Move((r, c), (to_r, to_c), piece, target))

        # --- Рокіровка ---
        legal_moves.extend(self._generate_castling_moves(color))

        # --- Фільтрація: відсіюємо ходи, що залишають короля під шахом ---
        truly_legal: list[Move] = []
        for move in legal_moves:
            self._make_move_internal(move)
            if not self.is_in_check(color):
                truly_legal.append(move)
            self._undo_move_internal(move)
        return truly_legal

    def _generate_castling_moves(self, color: str) -> list[Move]:
        """Повертає легальні ходи рокіровки для заданого кольору."""
        moves: list[Move] = []
        rights = self.castling_rights[color]
        if not (rights["kingside"] or rights["queenside"]):
            return moves

        king_pos = self.board.find_king(color)
        if king_pos is None:
            return moves
        king_row, king_col = king_pos
        king = self.board.get_piece(king_row, king_col)
        if king is None or king.has_moved or self.is_in_check(color):
            return moves

        enemy = BLACK if color == WHITE else WHITE

        # Коротка рокіровка (kingside): король g, тура h -> f.
        if rights["kingside"]:
            rook = self.board.get_piece(king_row, 7)
            if (isinstance(rook, Rook) and not rook.has_moved
                    and rook.color == color
                    and self.board.get_piece(king_row, 5) is None
                    and self.board.get_piece(king_row, 6) is None
                    and not self._square_attacked(king_row, 5, enemy)
                    and not self._square_attacked(king_row, 6, enemy)):
                moves.append(Move((king_row, king_col), (king_row, 6),
                                  king, is_castle_kingside=True))

        # Довга рокіровка (queenside): король c, тура a -> d.
        if rights["queenside"]:
            rook = self.board.get_piece(king_row, 0)
            if (isinstance(rook, Rook) and not rook.has_moved
                    and rook.color == color
                    and self.board.get_piece(king_row, 1) is None
                    and self.board.get_piece(king_row, 2) is None
                    and self.board.get_piece(king_row, 3) is None
                    and not self._square_attacked(king_row, 3, enemy)
                    and not self._square_attacked(king_row, 2, enemy)):
                moves.append(Move((king_row, king_col), (king_row, 2),
                                  king, is_castle_queenside=True))
        return moves

    def _square_attacked(self, row: int, col: int, by_color: str) -> bool:
        """Чи атакована клітина (row, col) фігурами кольору by_color?"""
        for r, c, piece in self.board.all_pieces(by_color):
            # У пішаків «атака» — лише по діагоналі, отже окремий випадок.
            if isinstance(piece, Pawn):
                direction = -1 if piece.color == WHITE else 1
                if r + direction == row and (c - 1 == col or c + 1 == col):
                    return True
            else:
                if (row, col) in piece.get_pseudo_legal_moves(self.board, r, c):
                    return True
        return False

    def is_in_check(self, color: str) -> bool:
        """Чи перебуває король заданого кольору під шахом?"""
        king_pos = self.board.find_king(color)
        if king_pos is None:
            return False
        enemy = BLACK if color == WHITE else WHITE
        return self._square_attacked(king_pos[0], king_pos[1], enemy)

    # ====================================================================
    #                       Виконання ходу
    # ====================================================================

    def make_move(self, move: Move) -> None:
        """
        Виконує хід, оновлює стан гри (історію, лічильники, права на
        рокіровку, en passant) і перемикає чергу ходу.
        """
        self._make_move_internal(move)

        # Оновлення прав на рокіровку.
        self._update_castling_rights_after(move)

        # Оновлення лічильника напівходів.
        if isinstance(move.piece, Pawn) or move.captured is not None:
            self.halfmove_clock = 0
        else:
            self.halfmove_clock += 1

        # Зміна гравця та номер ходу.
        if self.current_player == BLACK:
            self.fullmove_number += 1
        self.current_player = BLACK if self.current_player == WHITE else WHITE

        # Запис у історію та статистику повторень.
        self.move_history.append(move)
        key = self._position_key()
        self._position_counts[key] = self._position_counts.get(key, 0) + 1

    def _make_move_internal(self, move: Move) -> None:
        """
        Внутрішня версія: лише фізично переставляє фігури, оновлює en passant
        та запамʼятовує дані для undo_move. НЕ перемикає гравця і не пише в
        історію — використовується як для реальних ходів, так і для перевірки
        легальності.
        """
        move._prev_en_passant_target = self.board.en_passant_target
        move._prev_has_moved = move.piece.has_moved
        move._prev_halfmove_clock = self.halfmove_clock

        from_r, from_c = move.from_pos
        to_r, to_c = move.to_pos

        # Прибираємо бите фігуру.
        if move.is_en_passant:
            # «На проході» — береться пішак на сусідній клітині, не на цільовій.
            move._captured_pos = (from_r, to_c)
            self.board.set_piece(from_r, to_c, None)
        elif move.captured is not None:
            move._captured_pos = move.to_pos

        # Переміщення фігури.
        self.board.set_piece(from_r, from_c, None)
        self.board.set_piece(to_r, to_c, move.piece)
        move.piece.has_moved = True

        # Перетворення пішака.
        if move.promotion:
            promoted = piece_from_letter(move.promotion, move.piece.color)
            promoted.has_moved = True
            self.board.set_piece(to_r, to_c, promoted)

        # Рокіровка: переміщаємо туру.
        if move.is_castle_kingside:
            rook = self.board.get_piece(from_r, 7)
            self.board.set_piece(from_r, 5, rook)
            self.board.set_piece(from_r, 7, None)
            if rook:
                rook.has_moved = True
        elif move.is_castle_queenside:
            rook = self.board.get_piece(from_r, 0)
            self.board.set_piece(from_r, 3, rook)
            self.board.set_piece(from_r, 0, None)
            if rook:
                rook.has_moved = True

        # Оновлення en passant: лише після ходу пішака на 2 клітини.
        self.board.en_passant_target = None
        if isinstance(move.piece, Pawn) and abs(to_r - from_r) == 2:
            self.board.en_passant_target = ((from_r + to_r) // 2, from_c)

    def _undo_move_internal(self, move: Move) -> None:
        """
        Зворотна операція до _make_move_internal.
        Використовується для тимчасового виконання ходу при перевірці шахів
        та для перебору варіантів AI.
        """
        from_r, from_c = move.from_pos
        to_r, to_c = move.to_pos

        # Ставимо фігуру назад у початкову клітину
        # (для перетворення це знову буде пішак).
        self.board.set_piece(from_r, from_c, move.piece)
        move.piece.has_moved = move._prev_has_moved

        # Очищуємо цільову клітину (там було перетворення, або просто
        # переміщена фігура — вже відновлена).
        self.board.set_piece(to_r, to_c, None)

        # Відновлюємо взяту фігуру (якщо була).
        if move.captured is not None and move._captured_pos is not None:
            self.board.set_piece(move._captured_pos[0],
                                 move._captured_pos[1],
                                 move.captured)

        # Відкат рокіровки: повертаємо туру на місце.
        if move.is_castle_kingside:
            rook = self.board.get_piece(from_r, 5)
            self.board.set_piece(from_r, 7, rook)
            self.board.set_piece(from_r, 5, None)
            if rook:
                rook.has_moved = False
        elif move.is_castle_queenside:
            rook = self.board.get_piece(from_r, 3)
            self.board.set_piece(from_r, 0, rook)
            self.board.set_piece(from_r, 3, None)
            if rook:
                rook.has_moved = False

        # Відновлюємо en passant та лічильник.
        self.board.en_passant_target = move._prev_en_passant_target
        self.halfmove_clock = move._prev_halfmove_clock

    def undo_move(self) -> Move | None:
        """
        Скасовує останній зроблений хід (із оновленням ВСЬОГО стану).
        Повертає скасований хід або None, якщо історія порожня.
        """
        if not self.move_history:
            return None
        move = self.move_history.pop()
        # Видалити поточну позицію зі статистики повторень.
        key = self._position_key()
        if key in self._position_counts:
            self._position_counts[key] -= 1
            if self._position_counts[key] <= 0:
                del self._position_counts[key]

        # Відкотити чергу ходу.
        self.current_player = BLACK if self.current_player == WHITE else WHITE
        if self.current_player == BLACK:
            self.fullmove_number -= 1

        # Фізичний відкат.
        self._undo_move_internal(move)

        # Відновити права на рокіровку. Найпростіший спосіб — перерахувати
        # з нуля на основі історії. Щоб не зберігати окремо, дозволимо собі
        # реконструкцію за позиціями короля та тур.
        self._recompute_castling_rights()
        return move

    def _update_castling_rights_after(self, move: Move) -> None:
        """Знімає права на рокіровку після ходу короля чи тури."""
        # Хід короля — втрачаємо обидві рокіровки.
        if isinstance(move.piece, King):
            self.castling_rights[move.piece.color]["kingside"] = False
            self.castling_rights[move.piece.color]["queenside"] = False
        # Хід тури з кутового поля.
        if isinstance(move.piece, Rook):
            color = move.piece.color
            home_row = 7 if color == WHITE else 0
            if move.from_pos == (home_row, 0):
                self.castling_rights[color]["queenside"] = False
            elif move.from_pos == (home_row, 7):
                self.castling_rights[color]["kingside"] = False
        # Якщо взято тура суперника на її домашньому полі.
        if move.captured is not None and isinstance(move.captured, Rook):
            color = move.captured.color
            home_row = 7 if color == WHITE else 0
            if move.to_pos == (home_row, 0):
                self.castling_rights[color]["queenside"] = False
            elif move.to_pos == (home_row, 7):
                self.castling_rights[color]["kingside"] = False

    def _recompute_castling_rights(self) -> None:
        """
        Перераховує права на рокіровку «з нуля» на основі поточної позиції
        фігур та їхніх прапорців has_moved. Достатньо для коректної гри.
        """
        for color in (WHITE, BLACK):
            home_row = 7 if color == WHITE else 0
            king = self.board.get_piece(home_row, 4)
            self.castling_rights[color]["kingside"] = (
                isinstance(king, King) and king.color == color and not king.has_moved
                and isinstance(self.board.get_piece(home_row, 7), Rook)
                and not self.board.get_piece(home_row, 7).has_moved
            )
            self.castling_rights[color]["queenside"] = (
                isinstance(king, King) and king.color == color and not king.has_moved
                and isinstance(self.board.get_piece(home_row, 0), Rook)
                and not self.board.get_piece(home_row, 0).has_moved
            )

    # ====================================================================
    #                Стан партії: мат, пат, нічия
    # ====================================================================

    def is_checkmate(self) -> bool:
        """Чи поточному гравцю поставлений мат?"""
        return (self.is_in_check(self.current_player)
                and len(self.get_legal_moves()) == 0)

    def is_stalemate(self) -> bool:
        """Чи поточному гравцю поставлений пат?"""
        return (not self.is_in_check(self.current_player)
                and len(self.get_legal_moves()) == 0)

    def is_insufficient_material(self) -> bool:
        """
        Перевіряє нічию через недостатність матеріалу
        (король проти короля, король+слон проти короля, тощо).
        """
        pieces = [p for _, _, p in self.board.all_pieces()]
        types = [type(p).__name__ for p in pieces]
        # Тільки два королі.
        if len(pieces) == 2:
            return True
        # Король + (слон або кінь) проти одинокого короля.
        if len(pieces) == 3 and ("Bishop" in types or "Knight" in types):
            return True
        return False

    def is_fifty_move_rule(self) -> bool:
        """Правило 50 ходів (100 напівходів без взять і ходів пішаків)."""
        return self.halfmove_clock >= 100

    def is_threefold_repetition(self) -> bool:
        """Нічия за триразовим повторенням позиції."""
        return any(count >= 3 for count in self._position_counts.values())

    def is_game_over(self) -> bool:
        """Чи завершена партія з будь-якої причини?"""
        return (self.is_checkmate() or self.is_stalemate()
                or self.is_insufficient_material()
                or self.is_fifty_move_rule()
                or self.is_threefold_repetition())

    def get_result(self) -> str:
        """
        Повертає текстовий опис результату партії.
        Якщо гра не завершена — рядок "*".
        """
        if self.is_checkmate():
            winner = "Чорні" if self.current_player == WHITE else "Білі"
            return f"Мат! Перемогли {winner}."
        if self.is_stalemate():
            return "Пат. Нічия."
        if self.is_insufficient_material():
            return "Нічия (недостатньо матеріалу)."
        if self.is_fifty_move_rule():
            return "Нічия (правило 50 ходів)."
        if self.is_threefold_repetition():
            return "Нічия (триразове повторення)."
        return "*"

    # ====================================================================
    #                          Серіалізація
    # ====================================================================

    def _position_key(self) -> str:
        """Унікальний ключ позиції для виявлення повторень."""
        ep = ("-" if self.board.en_passant_target is None
              else Board.square_name(*self.board.en_passant_target))
        cr = (
            ("K" if self.castling_rights[WHITE]["kingside"] else "")
            + ("Q" if self.castling_rights[WHITE]["queenside"] else "")
            + ("k" if self.castling_rights[BLACK]["kingside"] else "")
            + ("q" if self.castling_rights[BLACK]["queenside"] else "")
        ) or "-"
        return f"{self.board.to_text()}|{self.current_player}|{cr}|{ep}"

    def save_to_file(self, path: str) -> None:
        """
        Зберігає поточний стан партії у текстовий файл.
        Формат:
            рядки 1-8 — клітини дошки;
            ep=... (опційно) — поле en passant;
            turn=white|black — чий хід;
            castle=KQkq — права на рокіровку;
            halfmove=NN — лічильник 50-ти ходів;
            fullmove=NN — номер ходу;
            moves: e2e4 e7e5 ...
        """
        lines = self.board.to_text().splitlines()
        # Прибираємо зайвий ep, якщо він уже у to_text — додамо власні параметри.
        # Перебудуємо «чисто»:
        lines = [ln for ln in lines if not ln.startswith("ep=")]
        if self.board.en_passant_target is not None:
            lines.append(f"ep={Board.square_name(*self.board.en_passant_target)}")
        lines.append(f"turn={self.current_player}")
        cr = (("K" if self.castling_rights[WHITE]["kingside"] else "")
              + ("Q" if self.castling_rights[WHITE]["queenside"] else "")
              + ("k" if self.castling_rights[BLACK]["kingside"] else "")
              + ("q" if self.castling_rights[BLACK]["queenside"] else "")) or "-"
        lines.append(f"castle={cr}")
        lines.append(f"halfmove={self.halfmove_clock}")
        lines.append(f"fullmove={self.fullmove_number}")
        moves_str = " ".join(m.to_algebraic() for m in self.move_history)
        lines.append(f"moves: {moves_str}")
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    @classmethod
    def load_from_file(cls, path: str) -> "GameState":
        """Завантажує стан партії з текстового файлу."""
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        gs = cls()
        gs.board = Board.from_text(text)
        # Дефолтні значення.
        gs.current_player = WHITE
        gs.halfmove_clock = 0
        gs.fullmove_number = 1
        gs.move_history = []
        gs._position_counts = {}
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("turn="):
                gs.current_player = line.split("=", 1)[1]
            elif line.startswith("castle="):
                value = line.split("=", 1)[1]
                gs.castling_rights[WHITE]["kingside"] = "K" in value
                gs.castling_rights[WHITE]["queenside"] = "Q" in value
                gs.castling_rights[BLACK]["kingside"] = "k" in value
                gs.castling_rights[BLACK]["queenside"] = "q" in value
            elif line.startswith("halfmove="):
                gs.halfmove_clock = int(line.split("=", 1)[1])
            elif line.startswith("fullmove="):
                gs.fullmove_number = int(line.split("=", 1)[1])
        # Зафіксувати поточну позицію в лічильнику повторень.
        gs._position_counts[gs._position_key()] = 1
        return gs
