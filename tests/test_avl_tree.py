# tests/test_avl_tree.py
import pytest

from dbdb.avl_tree import AVLTree
from dbdb.binary_tree import BinaryNode, BinaryNodeRef
from dbdb.logical import ValueRef
from tests.test_binary_tree import StubStorage


class TestAVLTreeHelpers:
    @pytest.fixture
    def tree(self):
        """An empty AVLTree instance with a stub storage."""
        return AVLTree(StubStorage())

    def test_get_height(self, tree):
        # Height of None is -1
        assert tree._get_height(None) == -1
        # Height of a leaf node is 0
        leaf = BinaryNode(BinaryNodeRef(), "k", ValueRef("v"), BinaryNodeRef(), 1, 0)
        assert tree._get_height(leaf) == 0

    def test_get_balance_factor_of_none_is_zero(self, tree):
        assert tree._get_balance_factor(None) == 0

    def test_get_balance_factor_of_leaf_is_zero(self, tree):
        leaf = BinaryNode(BinaryNodeRef(), "k", ValueRef("v"), BinaryNodeRef(), 1, 0)
        assert tree._get_balance_factor(leaf) == 0

    def test_get_balance_factor_left_heavy(self, tree):
        #    b (h=1)
        #   /
        #  a (h=0)
        a = BinaryNode(
            BinaryNodeRef(), "a", ValueRef("v1"), BinaryNodeRef(), 1, height=0
        )
        b = BinaryNode(
            BinaryNodeRef(referent=a), "b", ValueRef("v2"), BinaryNodeRef(), 2, height=1
        )
        # Left subtree has height 0, right is -1. Factor = 0 - (-1) = 1
        assert tree._get_balance_factor(b) == 1

    def test_get_balance_factor_right_heavy(self, tree):
        #    b (h=1)
        #     \
        #      c (h=0)
        c = BinaryNode(
            BinaryNodeRef(), "c", ValueRef("v3"), BinaryNodeRef(), 1, height=0
        )
        b = BinaryNode(
            BinaryNodeRef(), "b", ValueRef("v2"), BinaryNodeRef(referent=c), 2, height=1
        )
        # Left subtree has height -1, right is 0. Factor = -1 - 0 = -1
        assert tree._get_balance_factor(b) == -1

    def test_get_balance_factor_very_left_heavy(self, tree):
        # This represents an unbalanced tree that needs rotation
        #    c (h=2)
        #   /
        #  b (h=1)
        # /
        # a (h=0)
        a = BinaryNode(BinaryNodeRef(), "a", ValueRef("v1"), BinaryNodeRef(), 1, 0)
        b = BinaryNode(
            BinaryNodeRef(referent=a), "b", ValueRef("v2"), BinaryNodeRef(), 2, 1
        )
        c = BinaryNode(
            BinaryNodeRef(referent=b), "c", ValueRef("v3"), BinaryNodeRef(), 3, 2
        )

        assert tree._get_balance_factor(c) == 2


class TestAVLRotaions:
    @pytest.fixture
    def tree(self):
        return AVLTree(StubStorage())

    def test_right_rotate_simple(self, tree):
        #    c (h=2)        b (h=1)
        #   /            /   \
        #  b (h=1)  ->  a (h=0) c (h=0)
        # /
        # a (h=0)
        # Build a left-heavy tree c -> b -> a manually
        a = BinaryNode(BinaryNodeRef(), "a", ValueRef("v1"), BinaryNodeRef(), 1, 0)
        b = BinaryNode(
            BinaryNodeRef(referent=a), "b", ValueRef("v2"), BinaryNodeRef(), 2, 1
        )
        c = BinaryNode(
            BinaryNodeRef(referent=b), "c", ValueRef("v3"), BinaryNodeRef(), 3, 2
        )

        # Perform right rotation on c
        new_root_ref = tree._right_rotate(c)
        new_root = tree._follow(new_root_ref)

        # Assert new structure and heights
        assert new_root.key == "b"
        assert new_root.height == 1
        assert tree._follow(new_root.left_ref).key == "a"
        assert tree._get_height(tree._follow(new_root.left_ref)) == 0
        assert tree._follow(new_root.right_ref).key == "c"
        assert tree._get_height(tree._follow(new_root.right_ref)) == 0

    def test_left_rotate_simple(self, tree):
        # a (h=2)               b (h=1)
        #  \                   /     \
        #   b (h=1)   ->    a (h=0)  c (h=0)
        #    \
        #     c (h=0)
        # Build a right-heavy tree a -> b -> c manually
        c = BinaryNode(BinaryNodeRef(), "c", ValueRef("v3"), BinaryNodeRef(), 1, 0)
        b = BinaryNode(
            BinaryNodeRef(), "b", ValueRef("v2"), BinaryNodeRef(referent=c), 2, 1
        )
        a = BinaryNode(
            BinaryNodeRef(), "a", ValueRef("v1"), BinaryNodeRef(referent=b), 3, 2
        )

        # Perform left rotation on a
        new_root_ref = tree._left_rotate(a)
        new_root = tree._follow(new_root_ref)

        # Assert new structure and heights
        assert new_root.key == "b"
        assert new_root.height == 1
        assert tree._follow(new_root.left_ref).key == "a"
        assert tree._get_height(tree._follow(new_root.left_ref)) == 0
        assert tree._follow(new_root.right_ref).key == "c"
        assert tree._get_height(tree._follow(new_root.right_ref)) == 0
