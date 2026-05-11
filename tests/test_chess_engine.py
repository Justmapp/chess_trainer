"""
tests/test_chess_engine.py
==========================
Юніт-тести для шахового двигуна.

Запуск:
    python -m unittest tests.test_chess_engine
    або
    python tests/test_chess_engine.py
"""

import os
import sys
import unittest
import tempfile

# Дозволяємо запуск як скрипта (без -m).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from chess_engine import (
    GameState, ChessAI, Board, Move,
    King, Queen, Rook, Bishop, Knight, Pawn, WHITE, BLACK
)


class TestBoardInitialization(unittest.TestCase):
    """Тестування правильності початкової розстановки."""

    def test_starting_position_has_32_pieces(self):
        gs = GameState()
        pieces = list(gs.board.all_pieces())
        self.assertEqual(len(pieces), 32)

    def test_starting_position_legal_moves_count(self):
        """У початковій позиції в білих рівно 20 легальних ходів."""
        gs = GameState()
        self.assertEqual(len(gs.get_legal_moves()), 20)

    def test_kings_on_correct_squares(self):
        gs = GameState()
        self.assertEqual(gs.board.find_king(WHITE), (7, 4))
        self.assertEqual(gs.board.find_king(BLACK), (0, 4))


class TestPieceMovement(unittest.TestCase):
    """Тестування правил руху окремих фігур."""

    def test_knight_moves_from_corner(self):
        gs = GameState()
        gs.board.clear()
        gs.board.set_piece(7, 0, King(WHITE))
        gs.board.set_piece(0, 0, King(BLACK))
        gs.board.set_piece(4, 4, Knight(WHITE))
        moves = Knight(WHITE).get_pseudo_legal_moves(gs.board, 4, 4)
        self.assertEqual(len(moves), 8)

    def test_rook_blocked_by_friendly(self):
        gs = GameState()
        # На початку гри тура a1 нікуди не може ходити (навколо свої).
        moves = gs.board.get_piece(7, 0).get_pseudo_legal_moves(gs.board, 7, 0)
        self.assertEqual(moves, [])

    def test_pawn_double_move_only_from_start(self):
        gs = GameState()
        white_pawn = gs.board.get_piece(6, 4)  # e2
        moves = white_pawn.get_pseudo_legal_moves(gs.board, 6, 4)
        # e3 і e4
        self.assertIn((5, 4), moves)
        self.assertIn((4, 4), moves)


class TestSpecialMoves(unittest.TestCase):
    """Тестування спеціальних ходів: рокіровка, en passant, перетворення."""

    def test_castling_kingside(self):
        gs = GameState()
        # Прибираємо фігури між королем і турою.
        for c in [5, 6]:
            gs.board.set_piece(7, c, None)
        moves = gs.get_legal_moves()
        castles = [m for m in moves if m.is_castle_kingside]
        self.assertEqual(len(castles), 1)

    def test_no_castling_through_check(self):
        gs = GameState()
        for c in [5, 6]:
            gs.board.set_piece(7, c, None)
        # Прибираємо пішака f2 (білий) і пішака f7 (чорний),
        # щоб чорна тура з f8 атакувала клітину f1.
        gs.board.set_piece(6, 5, None)
        gs.board.set_piece(1, 5, None)
        gs.board.set_piece(0, 5, Rook(BLACK))
        moves = gs.get_legal_moves()
        self.assertFalse(any(m.is_castle_kingside for m in moves))

    def test_en_passant(self):
        gs = GameState()
        seq = ["e2e4", "a7a6", "e4e5", "d7d5"]
        for mv in seq:
            fr = Board.parse_square(mv[:2])
            to = Board.parse_square(mv[2:4])
            move = next(m for m in gs.get_legal_moves()
                        if m.from_pos == fr and m.to_pos == to)
            gs.make_move(move)
        ep = [m for m in gs.get_legal_moves() if m.is_en_passant]
        self.assertEqual(len(ep), 1)

    def test_promotion(self):
        gs = GameState()
        gs.board.clear()
        gs.board.set_piece(7, 0, King(WHITE))
        gs.board.set_piece(0, 7, King(BLACK))
        gs.board.set_piece(1, 4, Pawn(WHITE))
        gs.current_player = WHITE
        moves = gs.get_legal_moves()
        promos = [m for m in moves if m.promotion is not None]
        # 4 типи перетворень для одного цільового поля.
        self.assertEqual(len(promos), 4)


class TestCheckAndMate(unittest.TestCase):
    """Тестування виявлення шаху, мату й пату."""

    def test_simple_check(self):
        gs = GameState()
        gs.board.clear()
        gs.board.set_piece(7, 4, King(WHITE))
        gs.board.set_piece(0, 4, King(BLACK))
        gs.board.set_piece(4, 4, Rook(BLACK))
        self.assertTrue(gs.is_in_check(WHITE))

    def test_scholars_mate(self):
        gs = GameState()
        seq = ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]
        for mv in seq:
            fr = Board.parse_square(mv[:2])
            to = Board.parse_square(mv[2:4])
            move = next(m for m in gs.get_legal_moves()
                        if m.from_pos == fr and m.to_pos == to)
            gs.make_move(move)
        self.assertTrue(gs.is_checkmate())

    def test_stalemate(self):
        # Чорний король a8, білий король c7, білий ферзь b6 — класичний пат.
        gs = GameState()
        gs.board.clear()
        gs.board.set_piece(0, 0, King(BLACK))    # a8
        gs.board.set_piece(1, 2, King(WHITE))    # c7
        gs.board.set_piece(2, 1, Queen(WHITE))   # b6
        gs.current_player = BLACK
        self.assertTrue(gs.is_stalemate())
        self.assertFalse(gs.is_checkmate())

    def test_insufficient_material_two_kings(self):
        gs = GameState()
        gs.board.clear()
        gs.board.set_piece(0, 0, King(BLACK))
        gs.board.set_piece(7, 7, King(WHITE))
        self.assertTrue(gs.is_insufficient_material())


class TestUndoMove(unittest.TestCase):
    """Перевірка, що undo_move повертає стан повністю."""

    def test_undo_simple_move(self):
        gs = GameState()
        before_text = gs.board.to_text()
        before_player = gs.current_player
        move = next(m for m in gs.get_legal_moves()
                    if m.from_pos == (6, 4) and m.to_pos == (4, 4))
        gs.make_move(move)
        gs.undo_move()
        self.assertEqual(gs.board.to_text(), before_text)
        self.assertEqual(gs.current_player, before_player)

    def test_undo_capture(self):
        gs = GameState()
        # Зробимо обмін пішаками.
        for mv in ["e2e4", "d7d5", "e4d5"]:
            fr = Board.parse_square(mv[:2])
            to = Board.parse_square(mv[2:4])
            move = next(m for m in gs.get_legal_moves()
                        if m.from_pos == fr and m.to_pos == to)
            gs.make_move(move)
        # Скасовуємо взяття.
        gs.undo_move()
        # Чорний пішак має повернутись на d5.
        self.assertIsInstance(gs.board.get_piece(3, 3), Pawn)


class TestSerialization(unittest.TestCase):
    """Тестування збереження та завантаження партії."""

    def test_save_load_roundtrip(self):
        gs = GameState()
        for mv in ["e2e4", "e7e5", "g1f3", "b8c6"]:
            fr = Board.parse_square(mv[:2])
            to = Board.parse_square(mv[2:4])
            move = next(m for m in gs.get_legal_moves()
                        if m.from_pos == fr and m.to_pos == to)
            gs.make_move(move)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                           delete=False, encoding="utf-8") as f:
            path = f.name
        try:
            gs.save_to_file(path)
            gs2 = GameState.load_from_file(path)
            self.assertEqual(gs.board.to_text(), gs2.board.to_text())
            self.assertEqual(gs.current_player, gs2.current_player)
        finally:
            os.unlink(path)


class TestAI(unittest.TestCase):
    """Тестування шахового двигуна (AI)."""

    def test_ai_returns_legal_move(self):
        gs = GameState()
        ai = ChessAI(depth=2)
        move = ai.choose_best_move(gs)
        self.assertIsNotNone(move)
        self.assertIn(move, gs.get_legal_moves())

    def test_ai_finds_mate_in_one(self):
        """AI має знайти мат в один хід."""
        gs = GameState()
        gs.board.clear()
        gs.board.set_piece(0, 0, King(BLACK))
        gs.board.set_piece(2, 1, King(WHITE))
        gs.board.set_piece(7, 7, Rook(WHITE))   # тура на h1
        gs.board.set_piece(7, 0, Rook(WHITE))   # тура на a1
        gs.current_player = WHITE
        ai = ChessAI(depth=2)
        move = ai.choose_best_move(gs)
        gs.make_move(move)
        self.assertTrue(gs.is_checkmate())

    def test_ai_avoids_blunder(self):
        """AI має брати безкоштовного ферзя, якщо це безпечно."""
        gs = GameState()
        gs.board.clear()
        gs.board.set_piece(0, 0, King(BLACK))
        gs.board.set_piece(7, 7, King(WHITE))
        gs.board.set_piece(4, 4, Queen(BLACK))   # ферзь під боєм
        gs.board.set_piece(4, 0, Rook(WHITE))    # тура атакує по 4 ряду
        gs.current_player = WHITE
        ai = ChessAI(depth=2)
        move = ai.choose_best_move(gs)
        # Тура має взяти ферзя.
        self.assertEqual(move.to_pos, (4, 4))


if __name__ == "__main__":
    unittest.main(verbosity=2)
