"""
Модуль ai.py
============
Містить клас ChessAI — простий шаховий двигун (тренувальний AI).

Алгоритм:
    Мінімакс з альфа-бета відсіченнями (Alpha-Beta Pruning).
    Глибина пошуку настроюється параметром depth (за замовч. 2-3 півходи).

Оцінювання позиції (evaluation function):
    1) матеріальна перевага (сума цінностей фігур);
    2) позиційні бонуси через піщано-квадратні таблиці (PST) — для кожного
       типу фігури окрема матриця 8х8, яка кодує «де добре стояти»;
    3) штраф/бонус за наявність шаху, мата, пата.
"""

import random

from chess_engine.game import GameState
from chess_engine.move import Move
from chess_engine.pieces import (
    Piece, King, Queen, Rook, Bishop, Knight, Pawn, WHITE, BLACK
)

# ============================================================================
#   Піщано-квадратні таблиці (PST). Значення — для білих,
#   для чорних таблицю «перевертаємо» по вертикалі.
#   Розрахунок ведеться у сантипішаках (100 = 1 пішак).
# ============================================================================

_PAWN_PST = [
    [0,  0,  0,  0,  0,  0,  0,  0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [5,  5, 10, 25, 25, 10,  5,  5],
    [0,  0,  0, 20, 20,  0,  0,  0],
    [5, -5,-10,  0,  0,-10, -5,  5],
    [5, 10, 10,-20,-20, 10, 10,  5],
    [0,  0,  0,  0,  0,  0,  0,  0],
]

_KNIGHT_PST = [
    [-50,-40,-30,-30,-30,-30,-40,-50],
    [-40,-20,  0,  0,  0,  0,-20,-40],
    [-30,  0, 10, 15, 15, 10,  0,-30],
    [-30,  5, 15, 20, 20, 15,  5,-30],
    [-30,  0, 15, 20, 20, 15,  0,-30],
    [-30,  5, 10, 15, 15, 10,  5,-30],
    [-40,-20,  0,  5,  5,  0,-20,-40],
    [-50,-40,-30,-30,-30,-30,-40,-50],
]

_BISHOP_PST = [
    [-20,-10,-10,-10,-10,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5, 10, 10,  5,  0,-10],
    [-10,  5,  5, 10, 10,  5,  5,-10],
    [-10,  0, 10, 10, 10, 10,  0,-10],
    [-10, 10, 10, 10, 10, 10, 10,-10],
    [-10,  5,  0,  0,  0,  0,  5,-10],
    [-20,-10,-10,-10,-10,-10,-10,-20],
]

_ROOK_PST = [
    [0,  0,  0,  0,  0,  0,  0,  0],
    [5, 10, 10, 10, 10, 10, 10,  5],
   [-5,  0,  0,  0,  0,  0,  0, -5],
   [-5,  0,  0,  0,  0,  0,  0, -5],
   [-5,  0,  0,  0,  0,  0,  0, -5],
   [-5,  0,  0,  0,  0,  0,  0, -5],
   [-5,  0,  0,  0,  0,  0,  0, -5],
    [0,  0,  0,  5,  5,  0,  0,  0],
]

_QUEEN_PST = [
    [-20,-10,-10, -5, -5,-10,-10,-20],
    [-10,  0,  0,  0,  0,  0,  0,-10],
    [-10,  0,  5,  5,  5,  5,  0,-10],
    [ -5,  0,  5,  5,  5,  5,  0, -5],
    [  0,  0,  5,  5,  5,  5,  0, -5],
    [-10,  5,  5,  5,  5,  5,  0,-10],
    [-10,  0,  5,  0,  0,  0,  0,-10],
    [-20,-10,-10, -5, -5,-10,-10,-20],
]

_KING_PST_MIDDLE = [
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-30,-40,-40,-50,-50,-40,-40,-30],
    [-20,-30,-30,-40,-40,-30,-30,-20],
    [-10,-20,-20,-20,-20,-20,-20,-10],
    [ 20, 20,  0,  0,  0,  0, 20, 20],
    [ 20, 30, 10,  0,  0, 10, 30, 20],
]

_PST_BY_TYPE = {
    Pawn:   _PAWN_PST,
    Knight: _KNIGHT_PST,
    Bishop: _BISHOP_PST,
    Rook:   _ROOK_PST,
    Queen:  _QUEEN_PST,
    King:   _KING_PST_MIDDLE,
}


class ChessAI:
    """
    Шаховий двигун, що використовує мінімакс з альфа-бета відсіченнями.

    Атрибути:
        depth (int): глибина пошуку у напівходах (1, 2, 3, ...).
                     Розумні значення для тренувальної гри: 2-3.
        nodes_searched (int): лічильник переглянутих позицій (для метрик).
    """

    # Максимально можлива оцінка (для мату).
    MATE_SCORE = 1_000_000

    def __init__(self, depth: int = 2) -> None:
        if depth < 1:
            raise ValueError("Глибина пошуку має бути не меншою за 1.")
        self.depth = depth
        self.nodes_searched = 0

    # --------------------- Інтерфейс ---------------------- #
    def choose_best_move(self, game: GameState) -> Move | None:
        """
        Обирає найкращий хід для поточного гравця.
        Повертає None, якщо легальних ходів немає (мат або пат).
        """
        self.nodes_searched = 0
        legal = game.get_legal_moves()
        if not legal:
            return None

        # Розіграш дебюту: для першого ходу — невелика випадковість, щоб
        # тренажер не зациклювався на однакових партіях.
        if len(game.move_history) < 2:
            random.shuffle(legal)

        # Білі максимізують, чорні мінімізують.
        is_maximizing = (game.current_player == WHITE)
        best_move: Move | None = None
        best_score = -self.MATE_SCORE if is_maximizing else self.MATE_SCORE
        alpha, beta = -self.MATE_SCORE, self.MATE_SCORE

        # Сортуємо ходи: захоплення першими — це сильно покращує відсічення.
        legal.sort(key=lambda m: 0 if m.captured is None else m.captured.VALUE,
                   reverse=True)

        for move in legal:
            game._make_move_internal(move)
            game.current_player = BLACK if game.current_player == WHITE else WHITE
            score = self._minimax(game, self.depth - 1, alpha, beta,
                                  not is_maximizing)
            game.current_player = BLACK if game.current_player == WHITE else WHITE
            game._undo_move_internal(move)

            if is_maximizing:
                if score > best_score:
                    best_score = score
                    best_move = move
                alpha = max(alpha, score)
            else:
                if score < best_score:
                    best_score = score
                    best_move = move
                beta = min(beta, score)

            if beta <= alpha:
                break

        return best_move if best_move is not None else legal[0]

    # ------------------------ Мінімакс --------------------------- #
    def _minimax(self, game: GameState, depth: int,
                 alpha: int, beta: int, maximizing: bool) -> int:
        """
        Класичний мінімакс із альфа-бета відсіченнями.

        :param game: поточний стан гри (МУСИТЬ бути після _make_move_internal
                     у викликача та з тимчасово зміненим current_player).
        :param depth: глибина, що залишилася.
        :param alpha: нижня межа (для білих).
        :param beta: верхня межа (для чорних).
        :param maximizing: True — хід білих, False — хід чорних.
        :return: оцінка позиції в сантипішаках.
        """
        self.nodes_searched += 1

        # Базовий випадок: досягли максимальної глибини або гру завершено.
        if depth == 0:
            return self._evaluate(game)

        moves = game.get_legal_moves()
        if not moves:
            # Мат або пат поточному гравцю.
            if game.is_in_check(game.current_player):
                # Чим швидший мат — тим краще.
                return -self.MATE_SCORE - depth if maximizing \
                    else self.MATE_SCORE + depth
            return 0  # пат — нічия

        # Сортування для якісного відсічення.
        moves.sort(key=lambda m: 0 if m.captured is None else m.captured.VALUE,
                   reverse=True)

        if maximizing:
            best = -self.MATE_SCORE
            for move in moves:
                game._make_move_internal(move)
                game.current_player = BLACK if game.current_player == WHITE else WHITE
                value = self._minimax(game, depth - 1, alpha, beta, False)
                game.current_player = BLACK if game.current_player == WHITE else WHITE
                game._undo_move_internal(move)
                if value > best:
                    best = value
                alpha = max(alpha, best)
                if beta <= alpha:
                    break
            return best
        else:
            best = self.MATE_SCORE
            for move in moves:
                game._make_move_internal(move)
                game.current_player = BLACK if game.current_player == WHITE else WHITE
                value = self._minimax(game, depth - 1, alpha, beta, True)
                game.current_player = BLACK if game.current_player == WHITE else WHITE
                game._undo_move_internal(move)
                if value < best:
                    best = value
                beta = min(beta, best)
                if beta <= alpha:
                    break
            return best

    # ------------------------ Оцінка ----------------------------- #
    def _evaluate(self, game: GameState) -> int:
        """
        Оцінка позиції: позитивне значення вигідне білим, негативне — чорним.
        Складається з матеріалу + позиційних бонусів за PST.
        """
        score = 0
        for r, c, piece in game.board.all_pieces():
            material = piece.VALUE
            pst = _PST_BY_TYPE.get(type(piece))
            positional = 0
            if pst is not None:
                # Для білих — пряма таблиця, для чорних — зеркальна.
                positional = pst[r][c] if piece.color == WHITE \
                    else pst[7 - r][c]
            sign = 1 if piece.color == WHITE else -1
            score += sign * (material + positional)
        return score
