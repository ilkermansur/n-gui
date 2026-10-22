"""test_db.py - veritabanı yardımcılarının (app/core/db.py) testleri.

Kim kullanır: pytest. Bellek içi SQLite ile tablo oluşturma ve okuma/yazmayı doğrular.
"""

from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, create_all_tables, get_session, init_database


class SampleNote(Base):
    """Yalnızca bu testte kullanılan küçük bir tablo."""

    __tablename__ = "test_sample_note"

    id: Mapped[int] = mapped_column(primary_key=True)
    text: Mapped[str] = mapped_column(String(100))


def test_memory_db_tables_created():
    """create_all_tables tabloyu kurar; bir satır yazılıp başka oturumda okunur."""
    init_database("sqlite:///:memory:")
    create_all_tables()

    with get_session() as session:
        session.add(SampleNote(text="merhaba"))
        session.commit()

    # Neden ayrı oturum: StaticPool sayesinde aynı bellek DB'sinin görüldüğünü kanıtlar.
    with get_session() as session:
        notes = session.scalars(select(SampleNote)).all()

    assert len(notes) == 1
    assert notes[0].text == "merhaba"
