"""navigation.py - düz NavItem listesini yan menü için ağaca çevirir.

Kim kullanır: layout.py (sidebar çizimi) ve main.py ("/" sayfası ilk menü öğesini bulur).
Nasıl bağlanır: kernel.collect_nav_items(user) düz bir liste verir; her öğe
parent_key ile ebeveynini gösterir. build_navigation_tree bu listeyi
NavNode ağacına çevirir; ebeveyni olmayan (sahipsiz) öğeler atılır.
"""

from dataclasses import dataclass, field

from app.core.plugin import NavItem


@dataclass
class NavNode:
    """Menü ağacındaki tek bir düğüm: öğenin kendisi ve alt düğümleri."""

    item: NavItem
    children: list["NavNode"] = field(default_factory=list)


def nav_sort_key(item: NavItem) -> tuple:
    """Sıralama anahtarı: önce order, eşitse label.

    Parametre: item - menü öğesi. Dönüş: (order, label) ikilisi.
    """
    return (item.order, item.label)


def build_navigation_tree(items: list[NavItem]) -> list[NavNode]:
    """NavItem listesinden sıralı bir menü ağacı kurar.

    Parametre: items - kernel.collect_nav_items sonucu.
    Dönüş: kök düğümlerin listesi (parent_key'i None olanlar).
    Ebeveyni bulunamayan öğeler ve döngü içindeki öğeler sonuçta yer almaz.
    """
    # Neden önce sıralanır: düğümler bu sırayla eklendiği için hem kökler
    # hem her düğümün children listesi kendiliğinden sıralı olur.
    sorted_items = sorted(items, key=nav_sort_key)

    # Adım 1: key -> NavNode sözlüğü.
    nodes_by_key: dict[str, NavNode] = {}
    for item in sorted_items:
        nodes_by_key[item.key] = NavNode(item=item)

    # Adım 2: her düğümü ebeveyninin children listesine ekle.
    roots: list[NavNode] = []
    for item in sorted_items:
        node = nodes_by_key[item.key]
        if item.parent_key is None:
            roots.append(node)
            continue
        if item.parent_key == item.key:
            # Neden: kendini ebeveyn gösteren öğe kendi çocuğu olursa çizim sonsuza gider.
            continue
        parent = nodes_by_key.get(item.parent_key)
        if parent is None:
            # Neden: ebeveyni silinmiş (sahipsiz) öğe menüde gösterilmez.
            continue
        parent.children.append(node)

    # Neden döngü güvenli: yalnızca kökler döndürülür. Bir düğümün tek ebeveyni
    # olduğu için kökten aşağı inen yol bir döngüye giremez; a -> b -> a gibi
    # döngüdeki düğümler hiçbir köke bağlanmadığından sonuçta görünmez.
    return roots


def find_first_page_path(nodes: list[NavNode]) -> str | None:
    """Ağaçta, menü sırasına göre adresi olan ilk öğenin adresini bulur.

    Parametre: nodes - build_navigation_tree sonucu (ya da bir düğümün children listesi).
    Dönüş: ilk adres; hiçbir öğenin adresi yoksa None.
    """
    for node in nodes:
        if node.item.path:
            return node.item.path
        # Neden: adresi olmayan grup düğümünde ilk sayfa çocuklarının içindedir.
        child_path = find_first_page_path(node.children)
        if child_path is not None:
            return child_path
    return None


def flatten_navigation_tree(nodes: list[NavNode]) -> list[NavItem]:
    """Ağacı menüdeki görünüş sırasıyla düz bir NavItem listesine çevirir.

    Parametre: nodes - build_navigation_tree sonucu.
    Dönüş: NavItem listesi. Sahipsiz öğeler ağaçta olmadığı için burada da yoktur
    (örneğin header'daki arama yalnızca menüde görünen öğeleri önerir).
    """
    result: list[NavItem] = []
    for node in nodes:
        result.append(node.item)
        result.extend(flatten_navigation_tree(node.children))
    return result
