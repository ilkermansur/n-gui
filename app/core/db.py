"""db.py - SQLAlchemy bağlantısı, oturum üretimi ve model taban sınıfı.

Kim kullanır: main (init_database, create_all_tables), eklentilerin modelleri
(Base'den türer) ve servisleri (get_session ile DB'ye erişir).
Nasıl bağlanır: main açılışta init_database() çağırır; motor ve oturum
fabrikası bu modülün değişkenlerinde saklanır. Eklentiler modellerini
setup sırasında import ettiği için create_all_tables() tüm tabloları bir kerede kurar.
"""

from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


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
