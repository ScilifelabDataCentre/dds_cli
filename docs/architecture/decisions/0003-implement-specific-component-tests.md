# 3. Implement Specific Component Tests

Date: 2025-08-04

## Status

Accepted

## Context

The pattern for UI components in the DDS GUI is to implement the Textual component class. This is to ensure uniformity over the application with consistent component styling and functionality.
Mostly, the UI components only feature styling (for example buttons and containers), but some components feature more complex functionality (for example modals and tree views). For the simpler UI components, no additional tests are needed as they are covered by the frameworks testing. For the more complex components with added logic additional testing is needed.

There are two options for the testing of the more complex components:

1. Test the UI components more thoroughly through integration test corresponding to the different userflows, or
2. Test the UI components in the integration tests **AND** with designated component tests.

Currently, the complex components are not reused between pages. The test coverage would be the same in both alternatives.
The following is an example of one of the "simpler" components. In this case the component only changes some of the styling of the parent class `Button` (from Textual) and therefore implementing a custom test for the functionality of the `DDSButton` would not give us anything.

```python
class DDSButton(Button):
    """Regular button widget with uppercase title.
    Args:
        label: The label to be displayed on the button.
    """

    def __init__(self, label: str, *args: Any, **kwargs: Any) -> None:
        super().__init__(label.upper(), *args, **kwargs)

    DEFAULT_CSS = """
    DDSButton {
        padding: 0 2 0 2;
    }
    DDSButton.wide {
        width: 100%;
    }
    """
```

For the more complex components, such as `DDSTreeView`, where the goal is to display the project contents in a "tree view" (thus something specifically implemented by us either by additional logic or combinations of textual components), it might make more sense to add component tests. It is however only planned to be used in one place at the moment, so its not an actual "reusable component", it is only treated as such for code readability and consistency. Adding "strict" component tests and integration tests would in this case produce partly duplicate test code.

## Decision

The component specific test will be omitted for the components only extending the Textual components with design element, but component specific tests will be added for components containing additional logic or complex implementation of Textual components. The components will continue being subject to testing in integration tests as well.

## Consequences

As the complex components are not reused between pages at the moment, duplicate testing schemas would arise but not necessarily increase the test coverage of the component.
