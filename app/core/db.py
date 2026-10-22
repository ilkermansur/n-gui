"""db.py - SQLAlchemy bağlantısı, oturum üretimi ve model taban sınıfı.

Kim kullanır: main (init_database, create_all_tables), eklentilerin modelleri
(Base'den türer) ve servisleri (get_session ile DB'ye erişir).
Nasıl bağlanır: main açılışta init_database() çağırır; motor ve oturum
fabrikası bu modülün değişkenlerinde saklanır. Eklentiler modellerini
setup sırasında import ettiği için create_all_tables() tüm tabloları bir kerede kurar.
"""

import logging
from pathlib import Path

from sqlalchemy import Engine, MetaData, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Bütün veritabanı modellerinin türediği taban sınıf."""


# Neden modül seviyesinde: uygulamada tek bir veritabanı var, her yer aynısını kullanmalı.
engine: Engine | None = None
session_factory: sessionmaker | None = None


def init_database(database_url: str) -> None:
    """Veritabanı motorunu ve oturum fabrikasını hazırlar.

    Parametre: database_url - SQLAlchemy adresi (örnek "sqlite:///data/app.db").
    Dönüş: yok. Sonuç modülün engine ve session_factory değişkenlerine yazılır.
    """
    global engine, session_factory

    if database_url.endswith(":memory:"):
        # Neden StaticPool: bellek DB'si her bağlantıda sıfırdan açılır;
        # tek bağlantıyı paylaşmak tüm oturumların aynı veriyi görmesini sağlar.
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        if database_url.startswith("sqlite:///"):
            # Neden: SQLite dosyası yazılmadan önce klasörü (örn. data/) var olmalı.
            database_file = Path(database_url.removeprefix("sqlite:///"))
            database_file.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(database_url)

    # Neden expire_on_commit=False: commit sonrası nesneler oturum kapansa da okunabilsin.
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)


def get_session() -> Session:
    """Yeni bir veritabanı oturumu döndürür.

    Kullanım: `with get_session() as session:`.
    Dönüş: Session. init_database çağrılmadıysa RuntimeError fırlatır.
    """
    if session_factory is None:
        raise RuntimeError("Veritabanı hazır değil: önce init_database() çağrılmalı.")
    return session_factory()


def create_all_tables() -> None:
    """Base'den türeyen ve import edilmiş tüm modellerin tablolarını oluşturur.

    Var olan tablolara dokunmaz. Dönüş: yok.
    """
    if engine is None:
        raise RuntimeError("Veritabanı hazır değil: önce init_database() çağrılmalı.")
    Base.metadata.create_all(engine)
    add_missing_columns(engine, Base.metadata)


def column_default_sql(column, dialect) -> str:
    """Sütunun sabit varsayılan değerini SQL metni olarak döndürür; yoksa boş metin.

    Parametreler: column - SQLAlchemy Column; dialect - motorun SQL lehçesi.
    Neden yalnızca sabit: datetime.now gibi fonksiyon varsayılanları SQL'e yazılamaz.
    """
    default = column.default
    if default is None or not default.is_scalar:
        return ""
    value = default.arg
    if isinstance(value, bool):
        # Neden: bool, int'in alt sınıfıdır; önce kontrol edilmeli.
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return ""


def add_missing_columns(target_engine: Engine, metadata: MetaData) -> list[str]:
    """Var olan tablolara modelde olup veritabanında olmayan sütunları ekler (basit göç).

    Parametreler: target_engine - veritabanı motoru; metadata - modellerin MetaData'sı.
    Dönüş: eklenen "tablo.sütun" adlarının listesi.
    Neden: create_all yalnızca eksik tabloları kurar. Bir eklenti modeline yeni sütun
    eklendiğinde eski kurulumlar elle ALTER TABLE gerektirmesin. Sütun silme, tip
    değiştirme ve yeniden adlandırma yapılmaz; bunlar elle yapılmalıdır.
    Yeni sütun NULL olabilir şekilde eklenir; sabit varsayılanı varsa eski satırlar onu alır.
    """
    added = []
    inspector = inspect(target_engine)
    existing_tables = inspector.get_table_names()
    for table in metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        existing_columns = []
        for column_info in inspector.get_columns(table.name):
            existing_columns.append(column_info["name"])
        for column in table.columns:
            if column.name in existing_columns:
                continue
            column_type = column.type.compile(dialect=target_engine.dialect)
            statement = "ALTER TABLE " + table.name + " ADD COLUMN " + column.name + " " + column_type
            default_sql = column_default_sql(column, target_engine.dialect)
            if default_sql:
                statement += " DEFAULT " + default_sql
            with target_engine.begin() as connection:
                connection.execute(text(statement))
            added.append(table.name + "." + column.name)
            logger.info("Veritabanına sütun eklendi: %s.%s", table.name, column.name)
    return added
