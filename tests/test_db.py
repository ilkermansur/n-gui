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


def test_add_missing_columns_extends_existing_table(tmp_path):
    """Modelde olup tabloda olmayan sütun eklenir; eski satırlar varsayılan değeri alır."""
    from sqlalchemy import Integer, MetaData, create_engine, inspect, text
    from sqlalchemy.orm import DeclarativeBase

    from app.core.db import add_missing_columns

    engine = create_engine("sqlite:///" + str(tmp_path / "eski.db"))
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE notes (id INTEGER PRIMARY KEY, title VARCHAR(50))"))
        connection.execute(text("INSERT INTO notes (id, title) VALUES (1, 'eski')"))

    class NewBase(DeclarativeBase):
        """Bu teste özel model tabanı (uygulamanın Base'ini kirletmesin)."""

        metadata = MetaData()

    class Note(NewBase):
        """Yeni sürümdeki model: iki yeni sütun."""

        __tablename__ = "notes"
        id: Mapped[int] = mapped_column(primary_key=True)
        title: Mapped[str] = mapped_column(String(50))
        status: Mapped[str] = mapped_column(String(20), default="acik")
        priority: Mapped[int] = mapped_column(Integer, default=3)

    added = add_missing_columns(engine, NewBase.metadata)
    assert sorted(added) == ["notes.priority", "notes.status"]
    column_names = [column["name"] for column in inspect(engine).get_columns("notes")]
    assert "status" in column_names and "priority" in column_names
    with engine.connect() as connection:
        row = connection.execute(text("SELECT status, priority FROM notes WHERE id = 1")).one()
    assert row[0] == "acik"
    assert row[1] == 3
    # İkinci çağrıda eklenecek bir şey kalmaz.
    assert add_missing_columns(engine, NewBase.metadata) == []
