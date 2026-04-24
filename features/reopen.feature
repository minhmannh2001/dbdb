# features/reopen.feature
Feature: Transparent reconnection after file replacement
  As a database user,
  I want my connection to automatically detect and recover from file replacement
  so that reads and writes always target the current live database,
  even when another process compacted the file while I was connected.

  Background:
    Given a database at a temporary path

  Scenario: Reading from a stale connection returns current data
    Given the database has key "city" set to "Hanoi"
    And another process replaces the file with key "city" set to "Saigon"
    When I read key "city" from the original connection
    Then the result should be "Saigon"

  Scenario: Writing to a stale connection goes to the new file
    Given the database has key "a" set to "1"
    And another process replaces the file with key "a" set to "1"
    When I set key "b" to "2" on the original connection and commit
    Then a fresh connection should have key "a" equal to "1"
    And a fresh connection should have key "b" equal to "2"

  Scenario: Deleting from a stale connection affects the new file
    Given the database has key "a" set to "1"
    And the database has key "b" set to "2"
    And I commit the original connection
    And another process replaces the file keeping both keys
    When I delete key "b" from the original connection and commit
    Then a fresh connection should have key "a" equal to "1"
    And a fresh connection should not have key "b"

  Scenario: Multiple writes in a session after replacement all land in the new file
    Given the database has key "a" set to "1"
    And another process replaces the file with key "a" set to "1"
    When I set key "b" to "2" on the original connection
    And I set key "c" to "3" on the original connection
    And I commit the original connection
    Then a fresh connection should have key "b" equal to "2"
    And a fresh connection should have key "c" equal to "3"

  Scenario: Write is safe when replacement happens between pre-lock check and lock acquisition
    Given the database has key "a" set to "original"
    And another process replaces the file with key "a" set to "compacted"
    When I set key "b" to "safe_write" bypassing the pre-lock check and commit
    Then a fresh connection should have key "a" equal to "compacted"
    And a fresh connection should have key "b" equal to "safe_write"
