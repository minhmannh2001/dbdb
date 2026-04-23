# features/dbdb_interface.feature
Feature: DBDB Public API
  As a user, I want a simple, high-level interface to interact with the database,
  without needing to manage the underlying Storage and BinaryTree manually.

  Scenario: Creating a DBDB instance
    Given a temporary file object
    When I create a DBDB instance with the file object
    Then the DBDB instance should be successfully created
    And the instance should have a private Storage object
    And the instance should have a private BinaryTree object

  Scenario: Setting and getting a key
    Given a DBDB instance with a temporary file
    When I set the key "a" to "1" in the database
    Then getting the key "a" from the database should return "1"

  Scenario: Deleting a key
    Given a DBDB instance with a temporary file
    When I set the key "a" to "1" in the database
    And I delete the key "a" from the database
    Then getting the key "a" from the database should raise a KeyError

  Scenario: Operations on a closed database fail
    Given a DBDB instance with a temporary file
    When I close the database instance
    Then setting the key "a" to "1" should raise a ValueError
    And getting the key "a" should raise a ValueError
    And deleting the key "a" should raise a ValueError
