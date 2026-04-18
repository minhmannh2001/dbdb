Feature: Physical storage
  As implementers of the physical layer
  we start by binding Storage to a file-like object.

  Scenario: Storage wraps a file-like object
    Given a binary in-memory file
    When we construct Storage with that file
    Then the storage exposes the same file handle
