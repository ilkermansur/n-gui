"""test_loader.py - eklenti keşfi, yükleme sırası ve hata yalıtımı testleri.

Kim kullanır: pytest. tests/fixture_plugins altındaki sahte eklentileri yükler.
"""

from pathlib import Path

from app.core.config import AppConfig
from app.core.kernel import Kernel
from app.core.loader import discover_plugins, load_plugins
from app.core.plugin import NavItem

FIXTURE_FOLDER = str(Path(__file__).parent / "fixture_plugins")
FIXTURE_PACKAGE = "tests.fixture_plugins"


def make_kernel(disabled=None) -> Kernel:
    """Test için kernel üretir. Parametre: disabled - kapalı eklenti listesi."""
    config = AppConfig()
    config.disabled_plugins = disabled or []
    return Kernel(config)


def test_discovers_folders():
    """Keşif, plugin.py olan klasörleri alfabetik döndürür."""
    found = discover_plugins(FIXTURE_FOLDER)
    assert found == ["alpha", "broken_setup", "needs_alpha", "needs_missing"]


def test_loads_in_dependency_order():
    """needs_alpha, alpha'dan sonra yüklenir."""
    kernel = make_kernel()
    load_plugins(kernel, FIXTURE_FOLDER, FIXTURE_PACKAGE)
    assert kernel.plugin_status["alpha"] == "loaded"
    assert kernel.plugin_status["needs_alpha"] == "loaded"
    names = [Path(folder).name for folder in kernel.loaded_plugin_folders]
    assert names.index("alpha") < names.index("needs_alpha")


def test_broken_plugin_marked_failed_and_others_load():
    """Bozuk setup 'failed:' olur, alpha yine yüklenir."""
    kernel = make_kernel()
    load_plugins(kernel, FIXTURE_FOLDER, FIXTURE_PACKAGE)
    assert kernel.plugin_status["broken_setup"].startswith("failed:")
    assert kernel.plugin_status["alpha"] == "loaded"


def test_missing_dependency_not_loaded():
    """Olmayan bağımlılık durumu yazılır."""
    kernel = make_kernel()
    load_plugins(kernel, FIXTURE_FOLDER, FIXTURE_PACKAGE)
    assert kernel.plugin_status["needs_missing"] == "missing dependency: yok"
    assert kernel.get_service("never") is None


def test_disabled_plugin_skipped():
    """Kapalı eklenti atlanır, ona bağlı olan eksik bağımlılık alır."""
    kernel = make_kernel(disabled=["alpha"])
    load_plugins(kernel, FIXTURE_FOLDER, FIXTURE_PACKAGE)
    assert kernel.plugin_status["alpha"] == "disabled"
    assert kernel.plugin_status["needs_alpha"] == "missing dependency: alpha"


def test_only_parameter():
    """only dışındakiler 'not selected' olur."""
    kernel = make_kernel()
    load_plugins(kernel, FIXTURE_FOLDER, FIXTURE_PACKAGE, only=["alpha"])
    assert kernel.plugin_status["alpha"] == "loaded"
    assert kernel.plugin_status["needs_alpha"] == "not selected"
    assert kernel.plugin_status["broken_setup"] == "not selected"


def good_provider(user):
    """Çalışan menü sağlayıcısı."""
    return [NavItem(key="a", label="A", icon="home", path="/a")]


def bad_provider(user):
    """Hata fırlatan menü sağlayıcısı."""
    raise RuntimeError("bozuk")


def test_nav_provider_error_is_isolated():
    """Bozuk provider diğerinin öğelerini engellemez."""
    kernel = make_kernel()
    kernel.add_nav_provider(bad_provider)
    kernel.add_nav_provider(good_provider)
    items = kernel.collect_nav_items(None)
    assert [item.key for item in items] == ["a"]
