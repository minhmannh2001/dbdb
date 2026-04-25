# dbdb/avl_tree.py
from __future__ import annotations
from typing import Optional

from dbdb.binary_tree import BinaryNode, BinaryNodeRef
from dbdb.logical import LogicalBase, ValueRef


class AVLTree(LogicalBase):
    """
    An AVL-balanced binary search tree.
    """

    node_ref_class = BinaryNodeRef

    def _get_height(self, node: Optional[BinaryNode]) -> int:
        """
        Get the height of a node. A leaf has height 0, and None has height -1.
        """
        if node is None:
            return -1
        return node.height

    def _get_balance_factor(self, node: Optional[BinaryNode]) -> int:
        """
        Get the balance factor of a node.
        A positive value means the left subtree is taller.
        A negative value means the right subtree is taller.
        """
        if node is None:
            return 0
        return self._get_height(self._follow(node.left_ref)) - self._get_height(
            self._follow(node.right_ref)
        )
