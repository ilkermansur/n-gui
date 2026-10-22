"""test_scheduler_jobs.py - ScriptScheduler (plugins/scheduler/jobs.py) testleri.

Kim kullanır: pytest.
Nasıl bağlanır: başlatılmamış bir BackgroundScheduler ve sahte bir scripts servisi
kullanır; böylece gerçek zamanlama beklemeden iş kurma mantığı denenir.
"""

from apscheduler.schedulers.background import BackgroundScheduler

from plugins.scheduler.jobs import ScriptScheduler


class FakeField:
    """Sahte alan: yalnızca name ve default taşır."""

    def __init__(self, name, default):
        self.name = name
        self.default = default


class FakeSpec:
    """Sahte ScriptSpec: yalnızca fields taşır."""

    def __init__(self, fields):
        self.fields = fields


class FakeScripts:
    """Sahte scripts servisi: parse ve execute çağrılarını kaydeder."""

    def __init__(self):
        self.executed = []
        self.fail = False

    def parse(self, script_id):
        """Sabit iki alanlı (biri varsayılansız) spec döndürür."""
        return FakeSpec([FakeField("city", "Ankara"), FakeField("note", None)])

    def execute(self, script_id, arguments, username, record_success=True):
        """Çağrıyı kaydeder; fail açıksa hata fırlatır."""
        if self.fail:
            raise RuntimeError("boom")
        self.executed.append((script_id, arguments, username))


def make_entry(script_id, mode="scheduled", schedule="*/5 * * * *", is_enabled=True):
    """Test için kayıt sözlüğü üretir."""
    return {"script_id": script_id, "mode": mode, "schedule": schedule, "is_enabled": is_enabled}


def make_scheduler():
    """Başlatılmamış zamanlayıcı ve sahte servisle ScriptScheduler kurar."""
    scripts = FakeScripts()
    return ScriptScheduler(BackgroundScheduler(), scripts), scripts


def test_only_enabled_scheduled_entries_get_jobs():
    """Yalnızca etkin, scheduled ve cron'u dolu kayıtlar iş olur."""
    script_scheduler, _ = make_scheduler()
    entries = [
        make_entry("a"),
        make_entry("b", is_enabled=False),
        make_entry("c", mode="form"),
        make_entry("d", schedule=""),
        make_entry("e", schedule=None),
    ]
    assert script_scheduler.sync_jobs(entries) == ["script:a"]
    assert [job.id for job in script_scheduler.scheduler.get_jobs()] == ["script:a"]


def test_invalid_cron_skipped():
    """Geçersiz cron atlanır, geçerli olan kurulur."""
    script_scheduler, _ = make_scheduler()
    entries = [make_entry("bad", schedule="not a cron"), make_entry("good")]
    assert script_scheduler.sync_jobs(entries) == ["script:good"]


def test_resync_removes_deleted_jobs():
    """Listeden çıkan script'in işi silinir."""
    script_scheduler, _ = make_scheduler()
    script_scheduler.sync_jobs([make_entry("a"), make_entry("b")])
    script_scheduler.sync_jobs([make_entry("b")])
    assert [job.id for job in script_scheduler.scheduler.get_jobs()] == ["script:b"]


def test_run_job_uses_defaults_and_scheduler_user():
    """run_job varsayılanı olan alanlarla 'scheduler' kullanıcısı adına çalıştırır."""
    script_scheduler, scripts = make_scheduler()
    script_scheduler.run_job("a")
    assert scripts.executed == [("a", {"city": "Ankara"}, "scheduler")]


def test_run_job_swallows_errors():
    """Hata veren iş istisna fırlatmaz."""
    script_scheduler, scripts = make_scheduler()

    scripts.fail = True
    script_scheduler.run_job("a")


def test_validate_schedule():
    """Geçerli cron boş mesaj, geçersiz ya da boş ifade hata mesajı döndürür."""
    script_scheduler = ScriptScheduler(BackgroundScheduler(), None)
    assert script_scheduler.validate_schedule("0 8 * * *") == ""
    assert script_scheduler.validate_schedule("") != ""
    assert script_scheduler.validate_schedule("99 * * * *") != ""
