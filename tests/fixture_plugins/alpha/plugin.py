"""Test eklentisi 'alpha': loader testlerinde kullanılan sahte eklenti."""

from app.core.plugin import Plugin


class FixturePlugin(Plugin):
    """Loader'ın davranışını denemek için yazılmış küçük eklenti."""

    plugin_id = "alpha"
    name = "alpha"
    requires = []

    def setup(self, kernel) -> None:
        """Eklentiyi kurar. Parametre: kernel. Dönüş: yok."""
        kernel.register_service("alpha_service", "alpha")
