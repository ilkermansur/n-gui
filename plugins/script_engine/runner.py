"""runner.py - script'leri ayrı bir Python sürecinde, zaman sınırıyla çalıştırır.

Kim kullanır: script motoru eklentisi (sonraki task'lar) ve testler.
Nasıl bağlanır: run_script() argümanları geçici bir JSON dosyasına yazar,
runner_shim.py'yi `python -I` ile başlatır ve stdout'taki son marker satırını
sonuç olarak ayırır. Geri kalan stdout `output_text` olur. Zaman aşımında alt
sürecin tüm süreç grubu öldürülür. Hiçbir durumda istisna fırlatmaz; sonuç
RunResult içinde döner. Not: süreç grubu (killpg) macOS/Linux içindir; Windows
burada desteklenmez.

"""

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass

# runner_shim.py içindeki RESULT_MARKER ile birebir aynı olmalıdır.
RESULT_MARKER = "__NGUI_RESULT__"
MAX_TEXT_LENGTH = 20000
SHIM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "runner_shim.py")


@dataclass
class RunResult:
    """Bir script çalıştırmasının sonucu.

    success: script hatasız bitti ve sonuç üretti mi.
    result: run() fonksiyonunun döndürdüğü (JSON'a uygun) değer; hata varsa None.
    output_text: script'in print çıktıları (marker satırı hariç, 20000 karaktere kırpılı).
    error_text: hata mesajı veya traceback (20000 karaktere kırpılı).
    duration_ms: çalışma süresi, milisaniye.
    timed_out: zaman aşımına uğradı mı.
    """

    success: bool
    result: object
    output_text: str
    error_text: str
    duration_ms: int
    timed_out: bool = False


def decode_partial_output(value):
    """Zaman aşımında gelen kısmi çıktıyı güvenle metne çevirir.

    Parametre: value - TimeoutExpired'dan gelen bytes, str veya None.
    Dönüş: str (None ise boş metin).
    """
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def split_result_line(stdout_text):
    """stdout'u çıktı metni ve marker satırı olarak ayırır.

    Parametre: stdout_text - alt sürecin tüm stdout metni.
    Dönüş: (output_text, result_json) çifti; marker yoksa result_json None.
    """
    lines = stdout_text.split("\n")
    result_json = None
    last_marker_index = -1
    for index, line in enumerate(lines):
        if line.startswith(RESULT_MARKER):
            last_marker_index = index

    if last_marker_index >= 0:
        result_json = lines[last_marker_index][len(RESULT_MARKER):]
        # Sadece SON marker sonuçtur; script kendi print'iyle marker yazmışsa
        # o satırlar çıktı olarak kalır.
        del lines[last_marker_index]

    output_text = "\n".join(lines)
    # Shim'in marker öncesi eklediği satır sonunu çıktıdan temizle.
    output_text = output_text.rstrip("\n")
    return output_text, result_json


def kill_process_group(process):
    """Alt süreci ve onun başlattığı tüm torun süreçleri öldürür.

    Parametre: process - subprocess.Popen nesnesi (start_new_session=True ile açılmış).
    Dönüş: yok.
    """
    # subprocess.run yalnızca doğrudan çocuğu öldürür; script'in başlattığı
    # süreçler arkada çalışmaya devam ederdi. Yeni oturumda çocuğun pid'i grup
    # kimliğidir, grubu öldürmek hepsini kapatır.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        # Süreç tam bu sırada kendiliğinden bitmiş; yapılacak bir şey yok.
        pass


def run_with_arguments_file(file_path, arguments_path, timeout_seconds):
    """Shim'i başlatır, bekler ve çıktıyı RunResult'a çevirir.

    Parametreler:
        file_path: çalıştırılacak .py dosyasının yolu.
        arguments_path: argümanların yazıldığı JSON dosyasının yolu.
        timeout_seconds: bu süre dolunca süreç grubu öldürülür.
    Dönüş: RunResult.
    """
    script_folder = os.path.dirname(os.path.abspath(file_path))
    # Neden -B: alt süreç script klasörüne __pycache__ yazmasın.
    command = [sys.executable, "-I", "-B", SHIM_PATH, file_path, arguments_path]
    child_env = dict(os.environ)
    child_env["PYTHONIOENCODING"] = "utf-8"

    started_at = time.monotonic()
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=script_folder,
        env=child_env,
        start_new_session=True,
    )
    try:
        stdout_text, stderr_text = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        kill_process_group(process)
        # Öldürdükten sonra kalan çıktıyı boşaltıp süreci toplarız.
        stdout_text, stderr_text = process.communicate()
        duration_ms = int((time.monotonic() - started_at) * 1000)
        output_text, _ = split_result_line(stdout_text or "")
        return RunResult(
            success=False,
            result=None,
            output_text=output_text[:MAX_TEXT_LENGTH],
            error_text="Zaman aşımı: %s saniye içinde bitmedi" % timeout_seconds,
            duration_ms=duration_ms,
            timed_out=True,
        )
    duration_ms = int((time.monotonic() - started_at) * 1000)

    output_text, result_json = split_result_line(stdout_text)
    output_text = output_text[:MAX_TEXT_LENGTH]
    stderr_text = stderr_text[:MAX_TEXT_LENGTH]

    if process.returncode != 0:
        if not stderr_text.strip():
            # sys.exit(3) veya sinyalle ölüm gibi durumlarda stderr boş kalır.
            stderr_text = "Script %s koduyla çıktı" % process.returncode
        return RunResult(False, None, output_text, stderr_text, duration_ms)

    if result_json is None:
        # Script run() bitmeden sys.exit(0) gibi bir şeyle çıkmış olabilir.
        return RunResult(False, None, output_text, "Script sonuç üretmedi", duration_ms)

    try:
        result = json.loads(result_json)
    except json.JSONDecodeError:
        return RunResult(False, None, output_text, "Sonuç JSON olarak okunamadı", duration_ms)

    return RunResult(True, result, output_text, stderr_text, duration_ms)


def run_script(file_path, arguments, timeout_seconds):
    """Script'i izole bir alt süreçte çalıştırır.

    Parametreler:
        file_path: çalıştırılacak .py dosyasının yolu.
        arguments: run(**arguments) ile verilecek sözlük.
        timeout_seconds: bu süre dolunca alt süreç grubu öldürülür.
    Dönüş: RunResult (hazırlık veya başlatma hatalarında da istisna fırlatmaz).
    """
    arguments_path = None
    # Neden abspath: alt süreç script klasöründe (cwd) başlar; göreli yol orada bozulur.
    file_path = os.path.abspath(file_path)
    try:
        # Argümanları komut satırı yerine dosyayla veriyoruz: uzunluk sınırı ve
        # kaçış (escape) sorunları olmasın, Türkçe karakterler bozulmasın.
        arguments_file = tempfile.NamedTemporaryFile(
            delete=False, suffix=".json", mode="w", encoding="utf-8"
        )
        arguments_path = arguments_file.name
        json.dump(arguments, arguments_file, ensure_ascii=False)
        arguments_file.close()
        return run_with_arguments_file(file_path, arguments_path, timeout_seconds)
    except Exception as error:
        # Serileştirilemeyen argüman, olmayan klasör gibi hazırlık hataları.
        return RunResult(False, None, "", "Script başlatılamadı: %s" % error, 0)
    finally:
        # Geçici dosya her durumda silinir.
        if arguments_path is not None and os.path.exists(arguments_path):
            os.unlink(arguments_path)
