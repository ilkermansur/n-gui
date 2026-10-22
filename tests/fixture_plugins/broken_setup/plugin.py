"""Test eklentisi 'broken_setup': loader testlerinde kullanılan sahte eklenti."""

from app.core.plugin import Plugin


class FixturePlugin(Plugin):
    """Loader'ın davranışını denemek için yazılmış küçük eklenti."""

    plugin_id = "broken_setup"
    name = "broken_setup"
    requires = []

    def setup(self, kernel) -> None:
        """Eklentiyi kurar. Parametre: kernel. Dönüş: yok."""
        raise RuntimeError("bilerek bozuk")
