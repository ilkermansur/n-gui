"""plugin.py - ornek_eklenti_sablonu: yeni bir eklenti yazarken kopyalanacak en küçük örnek.

Kim kullanır: loader (eklenti klasörü bulunca setup'ı çağırır). Bu eklenti
config.toml içindeki [plugins] disabled listesinde olduğu için normalde YÜKLENMEZ;
yalnızca okunup kopyalanmak için durur.
Nasıl bağlanır:
- setup() içinde bir izin ("ornek_eklenti.view") ve bir menü sağlayıcı (nav provider) kaydeder.
- Aşağıdaki @ui.page fonksiyonu "/ornek-eklenti" sayfasını kaydeder. Sayfa, loader bu
  dosyayı import ettiği anda kaydolur; eklenti kapalıysa dosya import edilmez, sayfa da olmaz.
- Metinler bu klasördeki locales/tr.json ve locales/en.json dosyalarından gelir
  (i18n eklentisi yüklenen her eklentinin locales klasörünü kendiliğinden okur).

Yeni eklenti için adımlar (ayrıntı: docs/NASIL_CALISIR.md ve bu klasördeki README.md):
1. Bu klasörü plugins/yeni_adiniz/ olarak kopyalayın.
2. plugin_id değerini klasör adıyla aynı yapın; izin, adres ve çeviri anahtarlarını değiştirin.
3. config.toml'da eklentinin adı disabled listesinde OLMASIN.
Kural: eklentiler başka bir eklentiyi (plugins.X) import etmez; yalnızca app.core.*
modüllerini import eder ve diğer eklentilere kernel.get_service("ad") ile ulaşır.
"""

from nicegui import ui

from app.core.access import check_page_access
from app.core.kernel import get_kernel
from app.core.layout import create_shell_frame
from app.core.plugin import NavItem, Plugin
from app.core.text import t
from app.core.theme import LABEL_CLASSES
from app.core.widgets import page_card, stat_card

# Sayfanın adresi ve izin anahtarı tek yerde dursun diye sabit olarak tanımlanır.
PAGE_PATH = "/ornek-eklenti"
VIEW_PERMISSION = "ornek_eklenti.view"


class OrnekEklentiSablonuPlugin(Plugin):
    """Bir menü öğesi ve bir sayfa ekleyen örnek eklenti."""

    # plugin_id klasör adıyla aynı olmalıdır (loader klasör adını kullanır).
    plugin_id = "ornek_eklenti_sablonu"
    name = "ornek_eklenti_sablonu"
    version = "1.0"
    # Bu eklentiden ÖNCE yüklenmesi gereken eklentilerin klasör adları.
    # Biri yüklenemezse bu eklenti "missing dependency: ..." durumuyla atlanır.
    # Örnek boş bırakıldı: auth yoksa sayfa herkese açık, i18n yoksa anahtarlar görünür.
    requires = []

    def setup(self, kernel) -> None:
        """İzni ve menü sağlayıcısını kaydeder.

        Parametre: kernel - çekirdek. Dönüş: yok.
        Burada hata fırlarsa loader eklentiyi "failed" işaretler; uygulama yine açılır.
        """
        # Neden saklanır: menü sağlayıcısı (aşağıdaki metot) kernel'e ihtiyaç duyar.
        self.kernel = kernel
        # İzin anahtarı ve açıklaması (açıklama bir çeviri anahtarıdır).
        # Kayıtlı izinler Ayarlar > Roller ekranında seçilebilir hale gelir.
        kernel.register_permission(VIEW_PERMISSION, "ornek_eklenti.permission.view")
        # Menü sağlayıcısı: her sayfa çiziminde çağrılır ve NavItem listesi döndürür.
        # Bound method (self.build_nav_items) verildiği için lambda gerekmez.
        kernel.add_nav_provider(self.build_nav_items)

    def build_nav_items(self, user: dict | None) -> list[NavItem]:
        """Yan menüye eklenecek öğeleri döndürür (nav provider).

        Parametre: user - giriş yapmış kullanıcı sözlüğü ya da None.
        Dönüş: NavItem listesi; kullanıcının izni yoksa boş liste.
        """
        auth = self.kernel.get_service("auth")
        # Neden kontrol: menü yalnızca kullanıcının açabileceği sayfaları göstermeli.
        # auth eklentisi hiç yüklenmemişse yetki sistemi yoktur, öğe herkese görünür.
        if auth is not None and not auth.has_permission(user, VIEW_PERMISSION):
            return []

        item = NavItem(
            key="ornek_eklenti",
            label=t("ornek_eklenti.menu"),
            icon="extension",
            path=PAGE_PATH,
            # None: öğe kök seviyede durur. Bir bölümün altına koymak için
            # "section:<bolum_anahtari>" yazın (örnek "section:operation").
            parent_key=None,
            # Küçük sayı yukarıda görünür; hazır bölümler 10..50 arasındadır.
            order=90,
        )
        return [item]


# Neden modül seviyesinde: @ui.page NiceGUI'nin zorunlu dekoratörüdür ve sayfa,
# loader bu dosyayı import ettiği anda kaydolur.
@ui.page(PAGE_PATH)
def ornek_eklenti_page() -> None:
    """Örnek sayfa: önce yetki kontrolü, sonra kabuk çerçevesi, sonra içerik."""
    kernel = get_kernel()
    # Kural: her sayfanın ilk satırı açık bir yetki kontrolüdür. Giriş yoksa
    # /login'e gönderir, izin yoksa "yetkiniz yok" kartını çizer ve False döner.
    if not check_page_access(kernel, VIEW_PERMISSION):
        return

    # Header + sol menü çizilir; dönen kolonun içine sayfanın kendi kartları gelir.
    content = create_shell_frame(kernel, t("ornek_eklenti.title"))
    with content:
        with page_card().classes("gap-2"):
            ui.label(t("ornek_eklenti.title")).classes("text-lg font-semibold")
            ui.label(t("ornek_eklenti.description")).classes(LABEL_CLASSES)
        # Ortak bileşenler (app/core/widgets.py) her sayfanın aynı görünmesini sağlar.
        with ui.row().classes("w-full gap-4"):
            stat_card(t("ornek_eklenti.stat_plugins"), len(kernel.plugin_status))
            stat_card(t("ornek_eklenti.stat_permissions"), len(kernel.list_permissions()))
