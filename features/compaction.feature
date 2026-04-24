# features/compaction.feature
Feature: Database Compaction
  As a user, I want to compact the database file
  to reclaim space from overwritten or deleted data.

  Scenario: Compacting a database
    Given a database with overwritten data
    When I get the initial file size
    And I compact the database
    Then the new file size should be smaller
    And the database should contain the latest data
