Feature: Install smoke
  So that we know the editable package layout works
  we verify the top-level package imports.

  Scenario: dbdb package is importable
    Given the Python path includes the project layout
    When we import the dbdb package
    Then the dbdb package exposes a __file__ path
