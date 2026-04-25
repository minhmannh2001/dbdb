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
        left_child = BinaryNode(
            BinaryNodeRef(), "a", ValueRef("v1"), BinaryNodeRef(), 1, height=0
        )
        root = BinaryNode(
            BinaryNodeRef(referent=left_child),
            "b",
            ValueRef("v2"),
            BinaryNodeRef(),
            2,
            height=1,
        )
        # Left subtree has height 0, right is -1. Factor = 0 - (-1) = 1
        assert tree._get_balance_factor(root) == 1

    def test_get_balance_factor_right_heavy(self, tree):
        right_child = BinaryNode(
            BinaryNodeRef(), "c", ValueRef("v3"), BinaryNodeRef(), 1, height=0
        )
        root = BinaryNode(
            BinaryNodeRef(),
            "b",
            ValueRef("v2"),
            BinaryNodeRef(referent=right_child),
            2,
            height=1,
        )
        # Left subtree has height -1, right is 0. Factor = -1 - 0 = -1
        assert tree._get_balance_factor(root) == -1

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

        # Left subtree of c has height 1, right is -1. Factor = 1 - (-1) = 2
        assert tree._get_balance_factor(c) == 2
