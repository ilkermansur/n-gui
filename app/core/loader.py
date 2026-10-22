"""loader.py - plugins klasöründeki eklentileri bulur ve sırayla yükler.

Kim kullanır: uygulama başlangıcı (main) ve testler.
Nasıl bağlanır: her eklentinin plugin.py dosyası import edilir, içindeki
Plugin alt sınıfından örnek alınır, bağımlılık sırasına göre setup() çağrılır.
Sonuç kernel.plugin_status içine yazılır; bir eklentinin hatası diğerlerini durdurmaz.
"""

import importlib
import inspect
import logging
import os

from app.core.plugin import Plugin

logger = logging.getLogger(__name__)


def discover_plugins(folder: str) -> list[str]:
    """İçinde plugin.py olan alt klasör adlarını alfabetik döndürür.

    Parametre: folder - eklentilerin bulunduğu klasör. Dönüş: ad listesi.
    """
    if not os.path.isdir(folder):
        return []
    names = []
    for entry in sorted(os.listdir(folder)):
        if os.path.isfile(os.path.join(folder, entry, "plugin.py")):
            names.append(entry)
    return names


def find_plugin_class(module):
    """Modülde tanımlı Plugin alt sınıfını bulur; yoksa None döndürür."""
    for _, value in inspect.getmembers(module, inspect.isclass):
        # Neden: Plugin tabanı import edilmiş olarak da görünür, onu atlarız.
        if issubclass(value, Plugin) and value is not Plugin:
            return value
    return None


def load_plugins(kernel, folder: str, package: str, only: list[str] | None = None) -> None:
    """Eklentileri bulur, bağımlılık sırasına göre kurar, durumları yazar.

    Parametreler: kernel - çekirdek; folder - eklenti klasörü; package - import
    paket adı (örn. "plugins"); only - verilirse yalnızca bu eklentiler yüklenir.
    Dönüş: yok. Sonuç kernel.plugin_status ve kernel.loaded_plugin_folders içindedir.
    """
    # Aşama 1: import et ve örnek oluştur.
    pending: dict[str, Plugin] = {}
    for plugin_id in discover_plugins(folder):
        if only is not None and plugin_id not in only:
            kernel.plugin_status[plugin_id] = "not selected"
            continue
        if plugin_id in kernel.config.disabled_plugins:
            kernel.plugin_status[plugin_id] = "disabled"
            continue
        try:
            module = importlib.import_module(f"{package}.{plugin_id}.plugin")
            plugin_class = find_plugin_class(module)
            if plugin_class is None:
                raise RuntimeError("plugin.py içinde Plugin alt sınıfı yok")
            pending[plugin_id] = plugin_class()
        except Exception as error:
            logger.exception("Eklenti import edilemedi: %s", plugin_id)
            kernel.plugin_status[plugin_id] = f"failed: {error}"

    # Aşama 2: bağımlılığı hazır olanları kur; ilerleme kalmayana dek tekrarla.
    progress = True
    while pending and progress:
        progress = False
        for plugin_id in list(pending):
            plugin = pending[plugin_id]
            ready = True
            for required_id in plugin.requires:
                if kernel.plugin_status.get(required_id) != "loaded":
                    ready = False
            if not ready:
                continue

            del pending[plugin_id]
            progress = True
            # Neden: bozuk bir eklenti diğerlerinin yüklenmesini engellememeli.
            try:
                plugin.setup(kernel)
                kernel.plugin_status[plugin_id] = "loaded"
                kernel.loaded_plugin_folders.append(os.path.join(folder, plugin_id))
            except Exception as error:
                logger.exception("Eklenti kurulamadı: %s", plugin_id)
                kernel.plugin_status[plugin_id] = f"failed: {error}"

    # Kalanların bağımlılığı hiç yüklenemedi: ilk eksik olanı yaz.
    for plugin_id, plugin in pending.items():
        for required_id in plugin.requires:
            if kernel.plugin_status.get(required_id) != "loaded":
                kernel.plugin_status[plugin_id] = f"missing dependency: {required_id}"
                break
