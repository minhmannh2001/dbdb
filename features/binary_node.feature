Feature: Binary tree nodes and node references
  Node layout and BinaryNodeRef cooperate so a small subtree can be written
  to storage and rehydrated for navigation and value reads.

  Scenario: Chapter-shaped leaf survives persistence through the root reference
    Given empty storage over a binary memory buffer
    And a chapter-shaped leaf behind a root BinaryNodeRef
    When we persist that root reference
    And we load the tree root using only its disk address
    Then the node exposes the expected key and subtree length
    And the value slot reloads the UTF-8 payload from storage

  Scenario: From-node copy grows subtree length when the left branch reference grows
    Given a single-key leaf with placeholder child refs
    When we rebuild from-node with a stub left branch of larger subtree size
    Then the aggregate subtree length reflects the branch delta
