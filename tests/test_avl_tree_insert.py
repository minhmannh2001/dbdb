# tests/test_avl_tree_insert.py
import pytest

from dbdb.avl_tree import AVLTree
from dbdb.binary_tree import BinaryNodeRef
from dbdb.logical import ValueRef
from tests.test_binary_tree import StubStorage


class TestAVLTreeInsert:
    @pytest.fixture
    def tree(self):
        """An empty AVLTree instance with a stub storage."""
        return AVLTree(StubStorage())

    def _get_tree_structure(self, tree, root_ref):
        """
        Helper to get a dictionary representation of the tree for easy assertion.
        """
        if root_ref.address == 0 and root_ref._referent is None:  # Empty ref
            return None

        node = tree._follow(root_ref)
        if node is None:
            return None

        return {
            "key": node.key,
            "height": node.height,
            "left": self._get_tree_structure(tree, node.left_ref),
            "right": self._get_tree_structure(tree, node.right_ref),
        }

    def test_insert_simple_no_rebalance(self, tree):
        # Insert 3, 2, 4. Should form a balanced tree initially
        #   3
        #  / \
        # 2   4
        root_ref = tree._insert(None, "3", ValueRef("v3"))
        root_ref = tree._insert(tree._follow(root_ref), "2", ValueRef("v2"))
        root_ref = tree._insert(tree._follow(root_ref), "4", ValueRef("v4"))
        root = tree._follow(root_ref)

        assert root.key == "3"
        assert root.height == 1
        assert tree._follow(root.left_ref).key == "2"
        assert tree._get_height(tree._follow(root.left_ref)) == 0
        assert tree._follow(root.right_ref).key == "4"
        assert tree._get_height(tree._follow(root.right_ref)) == 0
        assert tree._get_balance_factor(root) == 0

    def test_insert_ll_case_right_rotate(self, tree):
        # Insert 3, 2, 1 -> needs right rotation
        # Before:   3(h=2)
        #          /
        #         2(h=1)
        #        /
        #       1(h=0)
        # After:    2(h=1)
        #          / \
        #         1(h=0) 3(h=0)
        root_ref = tree._insert(None, "3", ValueRef("v3"))
        root_ref = tree._insert(tree._follow(root_ref), "2", ValueRef("v2"))
        root_ref = tree._insert(tree._follow(root_ref), "1", ValueRef("v1"))
        root = tree._follow(root_ref)

        assert root.key == "2"
        assert root.height == 1
        assert tree._follow(root.left_ref).key == "1"
        assert tree._get_height(tree._follow(root.left_ref)) == 0
        assert tree._follow(root.right_ref).key == "3"
        assert tree._get_height(tree._follow(root.right_ref)) == 0
        assert tree._get_balance_factor(root) == 0

    def test_insert_rr_case_left_rotate(self, tree):
        # Insert 1, 2, 3 -> needs left rotation
        # Before:   1(h=2)
        #            \
        #             2(h=1)
        #              \
        #               3(h=0)
        # After:    2(h=1)
        #          / \
        #         1(h=0) 3(h=0)
        root_ref = tree._insert(None, "1", ValueRef("v1"))
        root_ref = tree._insert(tree._follow(root_ref), "2", ValueRef("v2"))
        root_ref = tree._insert(tree._follow(root_ref), "3", ValueRef("v3"))
        root = tree._follow(root_ref)

        assert root.key == "2"
        assert root.height == 1
        assert tree._follow(root.left_ref).key == "1"
        assert tree._get_height(tree._follow(root.left_ref)) == 0
        assert tree._follow(root.right_ref).key == "3"
        assert tree._get_height(tree._follow(root.right_ref)) == 0
        assert tree._get_balance_factor(root) == 0

    def test_insert_lr_case_left_right_rotate(self, tree):
        # Insert 3, 1, 2 -> needs left-right rotation
        # Before:   3(h=2)
        #          /
        #         1(h=1)
        #          \
        #           2(h=0)
        # After:    2(h=1)
        #          / \
        #         1(h=0) 3(h=0)
        root_ref = tree._insert(None, "3", ValueRef("v3"))
        root_ref = tree._insert(tree._follow(root_ref), "1", ValueRef("v1"))
        root_ref = tree._insert(tree._follow(root_ref), "2", ValueRef("v2"))
        root = tree._follow(root_ref)

        assert root.key == "2"
        assert root.height == 1
        assert tree._follow(root.left_ref).key == "1"
        assert tree._get_height(tree._follow(root.left_ref)) == 0
        assert tree._follow(root.right_ref).key == "3"
        assert tree._get_height(tree._follow(root.right_ref)) == 0
        assert tree._get_balance_factor(root) == 0

    def test_insert_rl_case_right_left_rotate(self, tree):
        # Insert 1, 3, 2 -> needs right-left rotation
        # Before:   1(h=2)
        #            \
        #             3(h=1)
        #            /
        #           2(h=0)
        # After:    2(h=1)
        #          / \
        #         1(h=0) 3(h=0)
        root_ref = tree._insert(None, "1", ValueRef("v1"))
        root_ref = tree._insert(tree._follow(root_ref), "3", ValueRef("v3"))
        root_ref = tree._insert(tree._follow(root_ref), "2", ValueRef("v2"))
        root = tree._follow(root_ref)

        assert root.key == "2"
        assert root.height == 1
        assert tree._follow(root.left_ref).key == "1"
        assert tree._get_height(tree._follow(root.left_ref)) == 0
        assert tree._follow(root.right_ref).key == "3"
        assert tree._get_height(tree._follow(root.right_ref)) == 0
        assert tree._get_balance_factor(root) == 0

    def test_insert_updates_existing_key(self, tree):
        root_ref = tree._insert(None, "a", ValueRef("v1"))
        root_ref = tree._insert(tree._follow(root_ref), "a", ValueRef("v2"))
        root = tree._follow(root_ref)

        assert root.key == "a"
        assert tree._follow(root.value_ref) == "v2"
        assert root.height == 0
        assert tree._get_balance_factor(root) == 0
