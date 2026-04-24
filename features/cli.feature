# features/cli.feature
Feature: Command-Line Interface (CLI) Tool
  As a user, I want to interact with the database from the command line
  to get, set, and delete keys.

  Scenario: Getting a key via CLI
    Given a database file "test.db" with key "a" set to "1"
    When I run the command "get a" on "test.db"
    Then the command should succeed
    And the standard output should be exactly "1"

  Scenario: Deleting a key via CLI
    Given a database file "test.db" with key "a" set to "1"
    When I run the command "delete a" on "test.db"
    And I run the command "get a" on "test.db"
    Then the command should fail

  Scenario: Deleting a missing key via CLI
    Given an empty database file "test.db"
    When I run the command "delete non-existent" on "test.db"
    Then the command should fail
    And the standard error should contain "Key not found"

