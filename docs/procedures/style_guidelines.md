# Coding Style Guide

As of writing (August 1st 2025), the code owners of this repository should adhere to the [Google Style Guide](https://google.github.io/styleguide/).

**Don't agree with a certain style?** Discuss with the team.

## Deviations from style guide

### Python

#### [Lint with Pylint](https://google.github.io/styleguide/pyguide.html#21-lint)

This repository does not currently use pylint. We will not be adding this while introducing this style guideline file. For formatting, we use Black.

#### [Imports](https://google.github.io/styleguide/pyguide.html#22-imports)

> Use `import` statements for packages and modules only, not for individual types, classes, or functions.

Whereas the above is what should be what's strived for, the code does import types, classes and functions in some locations. For now, this will be left as it is since it avoids some circular imports, but could be looked at a later time.

#### [Line length](https://google.github.io/styleguide/pyguide.html#32-line-length)

The maximum line length in this repository should be 120 characters, making it consistent with the dds_cli repository. Pylint is however not implemented in this repository at this time, and Black is currently not configured to use another formatting other than default, so the maximum number of characters per line is currently 88 via Black. If and when pylint is added, 120 characters should be added to the `.pylintrc`.
