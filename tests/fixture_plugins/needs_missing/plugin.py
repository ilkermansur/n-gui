"""Test eklentisi 'needs_missing': loader testlerinde kullanılan sahte eklenti."""

from app.core.plugin import Plugin


class FixturePlugin(Plugin):
    """Loader'ın davranışını denemek için yazılmış küçük eklenti."""

    plugin_id = "needs_missing"
    name = "needs_missing"
    requires = ["yok"]

    def setup(self, kernel) -> None:
        """Eklentiyi kurar. Parametre: kernel. Dönüş: yok."""
        kernel.register_service("never", "never")
