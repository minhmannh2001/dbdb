# tests/test_avl_tree_delete.py
import pytest

from dbdb.avl_tree import AVLTree
from dbdb.binary_tree import BinaryNode, BinaryNodeRef
from dbdb.logical import ValueRef
from tests.test_binary_tree import StubStorage


class TestAVLTreeDelete:
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

    def test_delete_from_empty_tree_raises_key_error(self, tree):
        with pytest.raises(KeyError):
            tree._delete(None, "a")

    def test_delete_non_existent_key_raises_key_error(self, tree):
        root_ref = tree._insert(None, "b", ValueRef("v2"))
        with pytest.raises(KeyError):
            tree._delete(tree._follow(root_ref), "a")

    def test_delete_leaf_node_no_rebalance(self, tree):
        #      b(h=1)           b(h=1)
        #     / \     ->         \
        #  a(h=0) c(h=0)       c(h=0)
        # delete leaf node 'a' (no rebalance needed)
        root_ref = tree._insert(None, "b", ValueRef("v2"))
        root_ref = tree._insert(tree._follow(root_ref), "a", ValueRef("v1"))
        root_ref = tree._insert(tree._follow(root_ref), "c", ValueRef("v3"))
        root = tree._follow(root_ref)
        assert root.key == "b"
        assert root.height == 1

        new_root_ref = tree._delete(root, "a")
        new_root = tree._follow(new_root_ref)

        assert new_root.key == "b"
        assert new_root.height == 1  # A node with one child has height 1
        assert tree._follow(new_root.left_ref) is None
        assert tree._follow(new_root.right_ref).key == "c"
        assert tree._get_height(tree._follow(new_root.right_ref)) == 0

    def test_delete_node_with_one_child_no_rebalance(self, tree):
        #      b(h=1)           a(h=0)
        #     /       ->       
        #  a(h=0)
        # delete node 'b' (node has one child, replace with child)
        root_ref = tree._insert(None, "b", ValueRef("v2"))
        root_ref = tree._insert(tree._follow(root_ref), "a", ValueRef("v1"))
        root = tree._follow(root_ref)
        assert root.key == "b"
        assert root.height == 1

        new_root_ref = tree._delete(root, "b")
        new_root = tree._follow(new_root_ref)

        assert new_root.key == "a"
        assert new_root.height == 0
        assert tree._follow(new_root.left_ref) is None
        assert tree._follow(new_root.right_ref) is None

    def test_delete_node_with_two_children_no_rebalance(self, tree):
        #      b(h=1)               c(h=1)
        #     / \       ->         /
        #  a(h=0) c(h=0)        a(h=0)
        # delete node 'b' (2 children → replace with inorder successor 'c')
        root_ref = tree._insert(None, "b", ValueRef("v2"))
        root_ref = tree._insert(tree._follow(root_ref), "a", ValueRef("v1"))
        root_ref = tree._insert(tree._follow(root_ref), "c", ValueRef("v3"))
        root = tree._follow(root_ref)
        assert root.key == "b"
        assert root.height == 1

        new_root_ref = tree._delete(root, "b")
        new_root = tree._follow(new_root_ref)

        assert new_root.key == "c"
        assert new_root.height == 1  # A node with one child has height 1
        assert tree._follow(new_root.left_ref).key == "a"
        assert tree._get_height(tree._follow(new_root.left_ref)) == 0
        assert tree._follow(new_root.right_ref) is None

    def test_delete_root_node_making_tree_empty(self, tree):
        root_ref = tree._insert(None, "a", ValueRef("v1"))
        root = tree._follow(root_ref)
        assert root.key == "a"
        assert root.height == 0

        new_root_ref = tree._delete(root, "a")
        assert new_root_ref.address == 0  # Should return an empty ref

    # Add tests for rebalancing cases after deletion
    def test_delete_ll_case_right_rotate(self, tree):
        # Build tree:
        #
        #          e (h=2)
        #         /       \
        #    b (h=1)     f (h=0)
        #     /    \
        # a (h=0)  c (h=0)
        root_ref = tree._insert(None, "e", ValueRef("v5"))
        root_ref = tree._insert(tree._follow(root_ref), "b", ValueRef("v2"))
        root_ref = tree._insert(tree._follow(root_ref), "f", ValueRef("v6"))
        root_ref = tree._insert(tree._follow(root_ref), "a", ValueRef("v1"))
        root_ref = tree._insert(tree._follow(root_ref), "c", ValueRef("v3"))

        root = tree._follow(root_ref)
        assert root.key == "e"
        assert root.height == 2
        # After insertion, the tree should be balanced with balance factor 1
        assert tree._get_balance_factor(root) == 1  # Left heavy

        # Delete 'f' → triggers right rotation at 'e' (balance factor of 'e' becomes +2)
        #
        # Resulting tree:
        #
        #          b (h=2)
        #         /       \
        #    a (h=0)     e (h=1)
        #               /
        #          c (h=0)
        #

        new_root_ref = tree._delete(root, "f")
        new_root = tree._follow(new_root_ref)

        assert new_root.key == "b"
        assert new_root.height == 2
        assert tree._follow(new_root.left_ref).key == "a"
        assert tree._get_height(tree._follow(new_root.left_ref)) == 0
        assert tree._follow(new_root.right_ref).key == "e"
        assert tree._get_height(tree._follow(new_root.right_ref)) == 1  # e has child c
        assert tree._get_balance_factor(new_root) == -1
        assert tree._follow(tree._follow(new_root.right_ref).left_ref).key == "c"
        assert (
            tree._get_height(tree._follow(tree._follow(new_root.right_ref).left_ref))
            == 0
        )
        assert tree._follow(tree._follow(new_root.right_ref).right_ref) is None

    def test_delete_rr_case_left_rotate(self, tree):
        # Build tree:
        #
        #          b (h=2)
        #         /       \
        #    a (h=0)     e (h=1)
        #               /       \
        #          c (h=0)     f (h=0)
        root_ref = tree._insert(None, "b", ValueRef("v2"))
        root_ref = tree._insert(tree._follow(root_ref), "a", ValueRef("v1"))
        root_ref = tree._insert(tree._follow(root_ref), "e", ValueRef("v5"))
        root_ref = tree._insert(tree._follow(root_ref), "c", ValueRef("v3"))
        root_ref = tree._insert(tree._follow(root_ref), "f", ValueRef("v6"))

        root = tree._follow(root_ref)
        assert root.key == "b"
        assert root.height == 2
        # After insertion, the tree should be balanced with balance factor -1
        assert tree._get_balance_factor(root) == -1  # Right heavy

        # Delete 'a' → triggers left rotation at 'b' (balance factor of 'b' becomes -2)
        #
        # Resulting tree:
        #
        #          e (h=2)
        #         /       \
        #    b (h=1)     f (h=0)
        #        \
        #     c (h=0)
        #
        new_root_ref = tree._delete(root, "a")
        new_root = tree._follow(new_root_ref)

        assert new_root.key == "e"
        assert new_root.height == 2
        assert tree._follow(new_root.left_ref).key == "b"
        assert tree._get_height(tree._follow(new_root.left_ref)) == 1  # b has child c
        assert tree._follow(new_root.right_ref).key == "f"
        assert tree._get_height(tree._follow(new_root.right_ref)) == 0
        assert tree._get_balance_factor(new_root) == 1
        assert tree._follow(tree._follow(new_root.left_ref).right_ref).key == "c"
        assert (
            tree._get_height(tree._follow(tree._follow(new_root.left_ref).right_ref))
            == 0
        )
        assert tree._follow(tree._follow(new_root.left_ref).left_ref) is None
