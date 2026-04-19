"""BDD: BinaryNode and BinaryNodeRef persistence and length rules."""

from pytest_bdd import scenario


@scenario("binary_node.feature", "Chapter-shaped leaf survives persistence through the root reference")
def test_binary_node_chapter_leaf_roundtrip_bdd():
    pass


@scenario(
    "binary_node.feature",
    "From-node copy grows subtree length when the left branch reference grows",
)
def test_binary_node_from_node_length_bdd():
    pass
