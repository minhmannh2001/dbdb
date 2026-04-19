Feature: Physical storage
  As implementers of the physical layer
  we start by binding Storage to a file-like object.

  Scenario: Storage wraps a file-like object
    Given a binary in-memory file
    When we construct Storage with that file
    Then the storage exposes the same file handle

  Scenario: Appended payload roundtrips through read at its address
    Given empty storage over a binary memory buffer
    When we append a known byte payload through write
    And we read the blob at that write address
    Then the read bytes equal the appended payload
