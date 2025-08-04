# 2. Use Project Centered Layout

Date: Spring 2025

## Status

Accepted

## Context

After meeting with end users it was found that:

- The UI should be simple and intuitive
- Core features such as uploading, downloading, and project managment should be focused on when designing the UI

Initial mockups featured a menu based layout, with menu items corresponding to the differend CLI group commands, but was decided against as all core features included project selection, hence a project centered one page layout was suggested.

## Decision

We will use a project centered layoud for the DDS GUI.

## Consequences

The GUI will be easier to navigate for end users and focus on the core features for these types of users. For administrative use, the project centered layout is not the most intuitive, so initially the CLI will be used for these operations. However, it would be possible to add new modules (project mode, admin mode) fot including administrative users in the GUI. 