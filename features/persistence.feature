# features/persistence.feature
Feature: Database Persistence
  As a user, I want to be able to store data in the database,
  close the connection, and find my data still there when I reopen it,
  ensuring data is not lost between sessions.

  Scenario: A key-value pair is persisted across sessions
    Given a new, empty database file
    When I connect to the database
    And I set the key "greeting" to the value "hello"
    And I commit the changes
    And I close the database
    When I reconnect to the database
    Then getting the key "greeting" should return the value "hello"

  Scenario: Uncommitted changes are not persisted
    Given a new, empty database file
    When I connect to the database
    And I set the key "status" to the value "temporary"
    And I close the database
    When I reconnect to the database
    Then getting the key "status" should result in an error

  Scenario: Getting a key from a new, empty database fails
    Given a new, empty database file
    When I connect to the database
    Then getting the key "any_key" should result in an error
