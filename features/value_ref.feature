Feature: Value references
  Callers of the logical layer persist UTF-8 text (and raw bytes) through Storage
  and reload values lazily by disk address.

  Scenario: UTF-8 text roundtrips through store and lazy get
    Given empty storage over a binary memory buffer
    And a ValueRef holding UTF-8 text
    When we store that reference on disk
    And we open a second ValueRef that only knows the stored address
    Then lazy get returns the original text

  Scenario: BytesValueRef rejects non-bytes referents at construction
    Then constructing BytesValueRef with a string referent raises TypeError
