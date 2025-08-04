# 3. Omit Specific Component Tests

Date: 2025-08-04

## Status

Accepted

## Context

The pattern for UI components in the DDS GUI is to implement the Textual component class. This is to ensure uniformity over the application with consistent component styling and functionality.
Mostly, the UI components only feature styling (for example buttons and containers), but some feature more complex funtionallity (for example modals and tree views). For the simpler UI componetns, no additionalal tests are needed as they are covered by the frameworks testsing. For the more complex components with added logic, these need additional testing.

There are two options for the testing of these components:

1. Test the UI components more thurughly through integration test corresponding to the different userflows, or
2. Test the UI components in the integration tests **AND** with designated component tests.

Currenly, the complex components are not resued between pages. The test converage would be the same in both alternatives.

## Decision

The component specific test will be omitted.

## Consequences

As the complex components are not resued between pages at the moment, duplicate testing schemas would not increase the readability of the test coverage of the componet. If the complex components are used in more than one page, we should bring this point up for discussion and reevaluate oour decision.
