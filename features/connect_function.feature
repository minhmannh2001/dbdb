# features/connect_function.feature
Feature: Top-level connect function
  As a user, I want a simple `connect()` function to open or create a database file
  without manually handling file objects.

  Scenario: Connecting to a non-existent file creates it
    Given a non-existent temporary database path
    When I connect to the database at that path
    Then a file should exist at that path
    And the connection should be a DBDB instance

  Scenario: Connecting to an existing file opens it
    Given a temporary database file with key "a" set to "1"
    When I connect to the database at that file's path
    Then getting the key "a" from the connection should return "1"
