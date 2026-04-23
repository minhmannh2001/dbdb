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
