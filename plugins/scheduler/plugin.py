"""plugin.py - scheduler eklentisi: scheduled script'leri cron programına göre çalıştırır.

Kim kullanır: loader (eklenti klasörü bulunca setup'ı çağırır).
Nasıl bağlanır: "scripts" servisini kullanır; "database.ready" ve "scripts.changed"
olaylarında işleri yeniden eşitler. Zamanlayıcı NiceGUI açılışında başlar, kapanışında durur.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from nicegui import app

from app.core.plugin import Plugin
from plugins.scheduler.jobs import ScriptScheduler


class SchedulerPlugin(Plugin):
    """Periyodik script çalıştırma eklentisi."""

    plugin_id = "scheduler"
    name = "scheduler"
    version = "1.0"
    requires = ["script_engine"]

    def setup(self, kernel) -> None:
        """Zamanlayıcıyı kurar, olaylara ve uygulama açılış/kapanışına bağlar.

        Parametre: kernel - çekirdek. Dönüş: yok.
        """
        self.kernel = kernel
        self.scripts = kernel.get_service("scripts")
        self.scheduler = BackgroundScheduler()
        self.script_scheduler = ScriptScheduler(self.scheduler, self.scripts)

        kernel.register_service("scheduler", self.script_scheduler)
        kernel.events.subscribe("database.ready", self.on_event)
        kernel.events.subscribe("scripts.changed", self.on_event)
        app.on_startup(self.on_startup)
        app.on_shutdown(self.on_shutdown)

    def sync_all(self) -> None:
        """Klasördeki script kayıtlarından işleri yeniden eşitler. Dönüş: yok."""
        entries = []
        for item in self.scripts.scan_folder():
            # Neden: kaydı olmayan (yayınlanmamış) ve sahipsiz script'ler çalışmaz.
            if item["entry"] is not None and not item["is_orphan"]:
                entries.append(item["entry"])
        self.script_scheduler.sync_jobs(entries)

    def on_event(self, data: dict) -> None:
        """Olay handler'ı: işleri eşitler. Parametre: data - olay verisi (kullanılmaz)."""
        self.sync_all()

    def on_startup(self) -> None:
        """NiceGUI açılışında zamanlayıcıyı başlatır ve işleri eşitler. Dönüş: yok."""
        self.sync_all()
        if not self.scheduler.running:
            self.scheduler.start()

    def on_shutdown(self) -> None:
        """NiceGUI kapanışında zamanlayıcıyı beklemeden durdurur. Dönüş: yok."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
