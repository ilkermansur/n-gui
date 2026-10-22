"""test_result_view.py - plugins/script_engine/result_view.py içindeki UI'sız yardımcıların testleri.

Kim kullanır: pytest.
Nasıl bağlanır: kernel kurulmadığı için t() çeviri anahtarının kendisini döndürür;
testler bu yüzden anahtarları karşılaştırır.
"""

from plugins.script_engine.result_view import display_value


def test_booleans_are_shown_as_yes_no():
    """True/False ekranda "Evet"/"Hayır" çevirisiyle gösterilir."""
    assert display_value(True) == "shell.yes"
    assert display_value(False) == "shell.no"


def test_none_is_shown_as_dash():
    """Boş değer "-" olarak gösterilir."""
    assert display_value(None) == "-"


def test_other_values_are_unchanged():
    """Sayı ve metin olduğu gibi kalır."""
    assert display_value(3) == 3
    assert display_value("abc") == "abc"
