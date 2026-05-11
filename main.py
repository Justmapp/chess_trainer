"""
main.py
=======
Точка входу до програми «Шаховий тренажер».
Запускає головне вікно tkinter (ChessApp).

Використання:
    python main.py

Залежності:
    Python 3.10+ (стандартна бібліотека, tkinter).
    Жодних сторонніх пакетів не потрібно.

Автор:
    Гриценко Р.О., група ІП-55, 2026
"""

from gui.app import ChessApp


def main() -> None:
    app = ChessApp()
    app.mainloop()


if __name__ == "__main__":
    main()
