"""runner_shim.py - script'i izole alt süreçte çalıştıran küçük giriş dosyası.

Kim kullanır: runner.py bu dosyayı `python -I runner_shim.py <script> <args.json>`
komutuyla ayrı bir Python sürecinde başlatır. Uygulamanın kendisi bu dosyayı
import ETMEZ.
Nasıl bağlanır: script dosyasını yükler, JSON dosyasındaki argümanlarla
run(**arguments) çağırır ve dönen değeri stdout'a RESULT_MARKER ile başlayan
bir satır olarak yazar. Hata olursa traceback stderr'e yazılır ve süreç 1
koduyla çıkar. Bu dosya app.* import etmez; tek başına çalışmalıdır.
"""

import importlib.util
import json
import os
import sys
import traceback

# runner.py içindeki RESULT_MARKER ile birebir aynı olmalıdır.
RESULT_MARKER = "__NGUI_RESULT__"


def load_script_module(script_path):
    """Script dosyasını modül olarak yükler.

    Parametre: script_path - çalıştırılacak .py dosyasının yolu.
    Dönüş: yüklenmiş modül nesnesi.
    """
    spec = importlib.util.spec_from_file_location("ngui_user_script", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    """Script'i yükler, run() çağırır ve sonucu marker satırı olarak yazar.

    Komut satırı: sys.argv[1] script yolu, sys.argv[2] argüman JSON dosyası.
    Dönüş: çıkış kodu (0 başarı, 1 hata).
    """
    script_path = sys.argv[1]
    arguments_path = sys.argv[2]

    # -I bayrağı script klasörünü sys.path'ten çıkarır; kardeş modüllerin
    # (yardımcı dosyaların) import edilebilmesi için başa ekliyoruz.
    sys.path.insert(0, os.path.dirname(os.path.abspath(script_path)))

    try:
        with open(arguments_path, encoding="utf-8") as arguments_file:
            arguments = json.load(arguments_file)
        module = load_script_module(script_path)
        result = module.run(**arguments)
        result_json = json.dumps(result, default=str, ensure_ascii=False)
    except Exception:
        traceback.print_exc()
        return 1

    # Script satır sonu olmadan print etmiş olabilir; marker her zaman kendi
    # satırında başlasın diye önce bir satır sonu yazıyoruz.
    sys.stdout.write("\n" + RESULT_MARKER + result_json + "\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
