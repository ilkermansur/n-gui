"""test_navigation.py - menü ağacı (build_navigation_tree) testleri.

Kim kullanır: pytest. NavItem listesinden ağaç kurulmasını, sahipsiz öğelerin
atılmasını, sıralamayı ve döngü korumasını doğrular.
"""

from app.core.navigation import (
    build_navigation_tree,
    find_first_page_path,
    flatten_navigation_tree,
)
from app.core.plugin import NavItem


def test_tree_nests_children():
    """section:a > group:1 > script:x şeklinde iç içe yerleşir."""
    items = [
        NavItem(key="script:x", label="X", icon="code", path="/script/x", parent_key="group:1"),
        NavItem(key="group:1", label="Grup 1", icon="folder", path="", parent_key="section:a"),
        NavItem(key="section:a", label="A", icon="home", path="/section/a"),
    ]
    tree = build_navigation_tree(items)

    assert len(tree) == 1
    assert tree[0].item.key == "section:a"
    assert len(tree[0].children) == 1
    assert tree[0].children[0].item.key == "group:1"
    assert len(tree[0].children[0].children) == 1
    assert tree[0].children[0].children[0].item.key == "script:x"


def test_orphan_items_dropped():
    """Ebeveyni bulunmayan öğe ağaçta hiç görünmez."""
    items = [
        NavItem(key="section:a", label="A", icon="home", path="/section/a"),
        NavItem(key="script:y", label="Y", icon="code", path="/script/y", parent_key="section:silinmis"),
    ]
    tree = build_navigation_tree(items)

    assert len(tree) == 1
    assert tree[0].item.key == "section:a"
    assert tree[0].children == []


def test_sorted_by_order_then_label():
    """Kökler ve çocuklar önce order, sonra label değerine göre sıralanır."""
    items = [
        NavItem(key="b", label="B", icon="", path="/b", order=10),
        NavItem(key="c", label="C", icon="", path="/c", order=5),
        NavItem(key="a", label="A", icon="", path="/a", order=10),
        NavItem(key="c2", label="Z", icon="", path="/c2", parent_key="c", order=1),
        NavItem(key="c1", label="Y", icon="", path="/c1", parent_key="c", order=1),
    ]
    tree = build_navigation_tree(items)

    root_keys = []
    for node in tree:
        root_keys.append(node.item.key)
    assert root_keys == ["c", "a", "b"]

    child_keys = []
    for node in tree[0].children:
        child_keys.append(node.item.key)
    assert child_keys == ["c1", "c2"]


def test_self_parent_does_not_loop():
    """Kendisini ebeveyn gösteren öğe sonsuz döngüye sokmaz ve ağaca girmez."""
    items = [
        NavItem(key="loop", label="Loop", icon="", path="/loop", parent_key="loop"),
        NavItem(key="ok", label="Ok", icon="", path="/ok"),
    ]
    tree = build_navigation_tree(items)

    assert len(tree) == 1
    assert tree[0].item.key == "ok"
    assert tree[0].children == []


def test_two_item_cycle_is_dropped():
    """Birbirini ebeveyn gösteren iki öğe (a -> b -> a) kökten erişilemez, atılır."""
    items = [
        NavItem(key="a", label="A", icon="", path="/a", parent_key="b"),
        NavItem(key="b", label="B", icon="", path="/b", parent_key="a"),
        NavItem(key="root", label="Root", icon="", path="/root"),
    ]
    tree = build_navigation_tree(items)

    assert len(tree) == 1
    assert tree[0].item.key == "root"


def test_find_first_page_path_skips_items_without_path():
    """Adresi olmayan grup atlanır, menü sırasındaki ilk adres döner."""
    items = [
        NavItem(key="group:1", label="Grup", icon="", path="", order=1),
        NavItem(key="script:x", label="X", icon="", path="/script/x", parent_key="group:1"),
        NavItem(key="later", label="Later", icon="", path="/later", order=50),
    ]
    tree = build_navigation_tree(items)

    assert find_first_page_path(tree) == "/script/x"
    assert find_first_page_path([]) is None


def test_flatten_tree_keeps_order_and_drops_orphans():
    """Ağaç düzleştirilince menü sırası korunur, sahipsiz öğe gelmez."""
    items = [
        NavItem(key="section:a", label="A", icon="", path="/a", order=1),
        NavItem(key="child", label="C", icon="", path="/c", parent_key="section:a"),
        NavItem(key="section:b", label="B", icon="", path="/b", order=2),
        NavItem(key="orphan", label="O", icon="", path="/o", parent_key="section:yok"),
    ]
    flat_items = flatten_navigation_tree(build_navigation_tree(items))

    keys = []
    for item in flat_items:
        keys.append(item.key)
    assert keys == ["section:a", "child", "section:b"]
