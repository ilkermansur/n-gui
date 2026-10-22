"""passwords.py - parolayı bcrypt ile özetleme ve doğrulama.

Kim kullanır: service.py (kullanıcı oluştururken ve giriş kontrolünde).
Nasıl bağlanır: yalnızca bcrypt paketine dayanır; veritabanı bilgisi yoktur.
"""

import bcrypt


def hash_password(plain: str) -> str:
    """Parolayı bcrypt ile özetler.

    Parametre: plain - düz parola. Dönüş: veritabanında saklanacak özet metni.
    """
    hashed_bytes = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed_bytes.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Düz parolanın kayıtlı özetle eşleşip eşleşmediğini söyler.

    Parametreler: plain - girilen parola; hashed - kayıtlı özet.
    Dönüş: eşleşirse True; özet bozuksa da False (hata fırlatmaz).
    """
    # Neden try: bozuk bir özet bütün girişi çökertmemeli, sadece başarısız olmalı.
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False
