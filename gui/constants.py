"""
Модуль constants.py
===================
Константи для графічного інтерфейсу шахового тренажера: розміри, кольори,
шрифти. Винесені в окремий файл для зручної модифікації.
"""

# Розміри.
SQUARE_SIZE = 72                 # розмір клітини у пікселях
BOARD_PIXEL_SIZE = SQUARE_SIZE * 8
COORD_MARGIN = 24                # поля для координат a-h, 1-8
SIDE_PANEL_WIDTH = 300           # бічна панель (історія, кнопки)

# Кольори клітин.
LIGHT_SQUARE_COLOR = "#F0D9B5"   # світло-бежевий
DARK_SQUARE_COLOR = "#B58863"    # коричневий

# Кольори підсвічування.
SELECTED_COLOR = "#7BA9D6"       # клітина обраної фігури
LEGAL_MOVE_COLOR = "#90C695"     # доступний хід
LAST_MOVE_COLOR = "#E8E36A"      # остання клітина (від/до)
CHECK_COLOR = "#E07171"          # король під шахом
SETUP_PLACEMENT_COLOR = "#A8D8B9"  # підказка в режимі тренажера

# Кольори фігур.
WHITE_PIECE_COLOR = "#FFFFFF"
WHITE_PIECE_OUTLINE = "#000000"
BLACK_PIECE_COLOR = "#1E1E1E"
BLACK_PIECE_OUTLINE = "#000000"

# Шрифти.
PIECE_FONT = ("DejaVu Sans", int(SQUARE_SIZE * 0.7))
COORD_FONT = ("Arial", 10, "bold")
PANEL_FONT = ("Arial", 10)
TITLE_FONT = ("Arial", 16, "bold")

# Параметри AI.
DEFAULT_AI_DEPTH = 2             # глибина пошуку за замовчуванням
MIN_AI_DEPTH = 1
MAX_AI_DEPTH = 4
