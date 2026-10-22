"""test_widgets.py - app/core/widgets.py içindeki UI'sız yardımcıların testleri.

Kim kullanır: pytest.
Nasıl bağlanır: yalnızca NiceGUI bağlamı gerektirmeyen shorten_stat_value test edilir.
"""

from app.core.widgets import STAT_VALUE_MAX_LENGTH, shorten_stat_value


def test_short_value_unchanged():
    """Kısa değer olduğu gibi kalır."""
    assert shorten_stat_value("127.0.0.1") == "127.0.0.1"


def test_long_value_is_cut_with_ellipsis():
    """Uzun değer sınırda kesilir ve sonuna … eklenir."""
    text = "x" * (STAT_VALUE_MAX_LENGTH + 10)
    shortened = shorten_stat_value(text)
    assert shortened == "x" * STAT_VALUE_MAX_LENGTH + "…"
