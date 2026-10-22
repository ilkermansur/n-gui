"""jobs.py - zamanlanmış script işlerini kuran ve çalıştıran sınıf.

Kim kullanır: plugins/scheduler/plugin.py ve tests/test_scheduler_jobs.py.
Nasıl bağlanır: bir APScheduler zamanlayıcısı ve "scripts" servisi verilir;
script kayıtlarındaki cron ifadelerini "script:<id>" anahtarlı işlere çevirir.
"""

import logging

from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

JOB_PREFIX = "script:"


class ScriptScheduler:
    """Yayınlanmış scheduled script'leri cron programına göre çalıştırır."""

    def __init__(self, scheduler, scripts_service) -> None:
        """Parametreler: scheduler - APScheduler örneği (başlatılmış olması gerekmez);
        scripts_service - "scripts" servisi. Dönüş: yok.
        """
        self.scheduler = scheduler
        self.scripts_service = scripts_service

    def sync_jobs(self, entries: list[dict]) -> list[str]:
        """Zamanlayıcıdaki işleri verilen kayıtlarla birebir eşitler.

        Parametre: entries - script kayıt sözlükleri (script_id, mode, schedule, is_enabled).
        Dönüş: kurulan işlerin anahtar listesi ("script:<id>").
        """
        wanted_job_ids = []
        for entry in entries:
            if entry.get("mode") != "scheduled" or not entry.get("is_enabled"):
                continue
            schedule = entry.get("schedule")
            if not schedule:
                continue
            job_id = JOB_PREFIX + entry["script_id"]
            try:
                trigger = CronTrigger.from_crontab(schedule)
            except ValueError:
                # Neden atlanır: bozuk bir cron diğer script'leri engellememeli.
                logger.error("Geçersiz cron ifadesi (%s): %r", entry["script_id"], schedule)
                continue
            # Neden önce silinir: başlatılmamış zamanlayıcıda replace_existing bekleyen
            # işleri ezmez, aynı iş iki kez birikirdi.
            if self.scheduler.get_job(job_id) is not None:
                self.scheduler.remove_job(job_id)
            self.scheduler.add_job(
                self.run_job,
                trigger,
                args=[entry["script_id"]],
                id=job_id,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=60,
            )
            wanted_job_ids.append(job_id)

        # Neden: silinen/devre dışı kalan script'in eski işi çalışmaya devam etmesin.
        for job in self.scheduler.get_jobs():
            if job.id.startswith(JOB_PREFIX) and job.id not in wanted_job_ids:
                self.scheduler.remove_job(job.id)
        return wanted_job_ids

    def run_job(self, script_id: str) -> None:
        """Script'i alan varsayılanlarıyla, "scheduler" kullanıcısı adına çalıştırır.

        Parametre: script_id. Dönüş: yok. Hata loglanır; zamanlayıcıyı asla durdurmaz.
        """
        try:
            spec = self.scripts_service.parse(script_id)
            defaults = {}
            for field in spec.fields:
                if field.default is not None:
                    defaults[field.name] = field.default
            self.scripts_service.execute(script_id, defaults, "scheduler")
        except Exception:
            logger.exception("Zamanlanmış script hata verdi: %s", script_id)
