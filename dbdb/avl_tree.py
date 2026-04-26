# dbdb/avl_tree.py
from __future__ import annotations
from typing import Any, Optional

from dbdb.binary_tree import BinaryNode, BinaryNodeRef
from dbdb.logical import LogicalBase, ValueRef


class AVLTree(LogicalBase):
    """
    An AVL-balanced binary search tree.
    """

    node_ref_class = BinaryNodeRef
    value_ref_class = ValueRef  # Keep this for now

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

    def _right_rotate(self, old_root: BinaryNode) -> BinaryNodeRef:
        """
        Performs a right rotation on the given old_root to rebalance the tree.
        Returns the new root of the subtree.
        """
        assert old_root is not None
        new_root = self._follow(old_root.left_ref)
        assert new_root is not None  # Should not happen if tree is balanced correctly

        # This is the subtree that moves from being new_root's right child
        # to old_root's left child.
        moved_subtree_ref = new_root.right_ref

        # 1. Update old_root: its new left child is the moved_subtree_ref
        old_root_updated = BinaryNode.from_node(old_root, left_ref=moved_subtree_ref)
        # Update height for old_root_updated
        old_root_updated = BinaryNode.from_node(
            old_root_updated,
            height=max(
                self._get_height(self._follow(old_root_updated.left_ref)),
                self._get_height(self._follow(old_root_updated.right_ref)),
            )
            + 1,
        )

        # 2. Update new_root: its new right child is old_root_updated
        new_root_updated = BinaryNode.from_node(
            new_root, right_ref=self.node_ref_class(referent=old_root_updated)
        )
        # Update height for new_root_updated
        new_root_updated = BinaryNode.from_node(
            new_root_updated,
            height=max(
                self._get_height(self._follow(new_root_updated.left_ref)),
                self._get_height(self._follow(new_root_updated.right_ref)),
            )
            + 1,
        )
        return self.node_ref_class(referent=new_root_updated)

    def _left_rotate(self, old_root: BinaryNode) -> BinaryNodeRef:
        """
        Performs a left rotation on the given old_root to rebalance the tree.
        Returns the new root of the subtree.
        """
        assert old_root is not None
        new_root = self._follow(old_root.right_ref)
        assert new_root is not None  # Should not happen if tree is balanced correctly

        # This is the subtree that moves from being new_root's left child
        # to old_root's right child.
        moved_subtree_ref = new_root.left_ref

        # 1. Update old_root: its new right child is the moved_subtree_ref
        old_root_updated = BinaryNode.from_node(old_root, right_ref=moved_subtree_ref)
        # Update height for old_root_updated
        old_root_updated = BinaryNode.from_node(
            old_root_updated,
            height=max(
                self._get_height(self._follow(old_root_updated.left_ref)),
                self._get_height(self._follow(old_root_updated.right_ref)),
            )
            + 1,
        )

        # 2. Update new_root: its new left child is old_root_updated
        new_root_updated = BinaryNode.from_node(
            new_root, left_ref=self.node_ref_class(referent=old_root_updated)
        )
        # Update height for new_root_updated
        new_root_updated = BinaryNode.from_node(
            new_root_updated,
            height=max(
                self._get_height(self._follow(new_root_updated.left_ref)),
                self._get_height(self._follow(new_root_updated.right_ref)),
            )
            + 1,
        )
        return self.node_ref_class(referent=new_root_updated)

    def _insert(
        self, node: Optional[BinaryNode], key: str, value_ref: ValueRef
    ) -> BinaryNodeRef:
        # 1. Perform standard BST insertion (recursive)
        if node is None:
            new_node = BinaryNode(
                self.node_ref_class(),
                key,
                value_ref,
                self.node_ref_class(),
                1,
                0,  # New leaf node has height 0
            )
            return self.node_ref_class(referent=new_node)

        if key < node.key:
            node_updated = BinaryNode.from_node(
                node,
                left_ref=self._insert(self._follow(node.left_ref), key, value_ref),
            )
        elif node.key < key:
            node_updated = BinaryNode.from_node(
                node,
                right_ref=self._insert(self._follow(node.right_ref), key, value_ref),
            )
        else:
            # Key already exists, update value
            node_updated = BinaryNode.from_node(node, value_ref=value_ref)

        # 2. Update height of the current node after insertion
        node_updated = BinaryNode.from_node(
            node_updated,
            height=max(
                self._get_height(self._follow(node_updated.left_ref)),
                self._get_height(self._follow(node_updated.right_ref)),
            )
            + 1,
        )

        # 3. Get the balance factor of this node
        balance = self._get_balance_factor(node_updated)

        # 4. Rebalance the node if it's unbalanced
        # Left Left Case
        if balance > 1 and key < self._follow(node_updated.left_ref).key:
            return self._right_rotate(node_updated)

        # Right Right Case
        if balance < -1 and key > self._follow(node_updated.right_ref).key:
            return self._left_rotate(node_updated)

        # Left Right Case
        if balance > 1 and key > self._follow(node_updated.left_ref).key:
            node_updated_left_ref = self._left_rotate(
                self._follow(node_updated.left_ref)
            )
            node_updated = BinaryNode.from_node(
                node_updated, left_ref=node_updated_left_ref
            )
            # Recalculate height after internal rotation and node update
            node_updated = BinaryNode.from_node(
                node_updated,
                height=max(
                    self._get_height(self._follow(node_updated.left_ref)),
                    self._get_height(self._follow(node_updated.right_ref)),
                )
                + 1,
            )
            return self._right_rotate(node_updated)

        # Right Left Case
        if balance < -1 and key < self._follow(node_updated.right_ref).key:
            node_updated_right_ref = self._right_rotate(
                self._follow(node_updated.right_ref)
            )
            node_updated = BinaryNode.from_node(
                node_updated, right_ref=node_updated_right_ref
            )
            # Recalculate height after internal rotation and node update
            node_updated = BinaryNode.from_node(
                node_updated,
                height=max(
                    self._get_height(self._follow(node_updated.left_ref)),
                    self._get_height(self._follow(node_updated.right_ref)),
                )
                + 1,
            )
            return self._left_rotate(node_updated)

        return self.node_ref_class(referent=node_updated)
