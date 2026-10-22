"""Test eklentisi 'needs_alpha': loader testlerinde kullanılan sahte eklenti."""

from app.core.plugin import Plugin


class FixturePlugin(Plugin):
    """Loader'ın davranışını denemek için yazılmış küçük eklenti."""

    plugin_id = "needs_alpha"
    name = "needs_alpha"
    requires = ["alpha"]

    def setup(self, kernel) -> None:
        """Eklentiyi kurar. Parametre: kernel. Dönüş: yok."""
        kernel.register_service("needs_alpha_service", "needs_alpha")
