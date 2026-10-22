"""test_theme.py - app/core/theme.py içindeki UI'sız yardımcıların testleri.

Kim kullanır: pytest.
Nasıl bağlanır: yalnızca NiceGUI bağlamı gerektirmeyen html_lang_script test edilir.
"""

from app.core.theme import html_lang_script


def test_script_sets_document_language():
    """Betik <html> öğesinin lang özelliğini verilen dile ayarlar."""
    assert html_lang_script("tr") == '<script>document.documentElement.lang = "tr";</script>'


def test_script_escapes_language_value():
    """Dil değeri tırnak içinde kaçışlanır; betiğin dışına taşamaz."""
    script = html_lang_script('x";alert(1);"')
    assert 'lang = "x\\";alert(1);\\"";' in script
