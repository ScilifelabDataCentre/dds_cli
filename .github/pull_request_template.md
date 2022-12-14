> **Before submitting the PR, please go through the sections below and fill in what you can. If there are any items that are irrelevant for the current PR, remove the row. If a relevant option is missing, please add it as an item and add a PR comment informing that the new option should be included into this template.**

> **All _relevant_ items should be ticked before the PR is merged**

# Description

- [ ] Summary of the changes and the related issue:
- [ ] Motivation and context regarding why the change is needed:
- [ ] List / description of any dependencies or other changes required for this change:
- Fixes an issue in GitHub / Jira:
  - [ ] Yes: _[link to GitHub issue / Jira task ID]_
  - [ ] No

## Type of change

- [ ] Bug fix
  - [ ] Breaking: _Describe_
  - [ ] Non-breaking
- [ ] Documentation
- [ ] New feature
  - [ ] Breaking: _Describe_
  - [ ] Non-breaking
- [ ] Security Alert fix
- [ ] Tests **(only)**
- [ ] Workflow

_"Breaking": The change will cause existing functionality to not work as expected._

# Checklist:

## General

- [ ] [Changelog](../CHANGELOG.md): New row added. Not needed when PR includes _only_ tests.
- [ ] Code change
  - [ ] Self-review of code done
  - [ ] Comments added, particularly in hard-to-understand areas
  - Documentation update
    - [ ] Done
    - [ ] Not needed

## Repository / Releases

- [ ] Blocking PRs have been merged
- [ ] Rebase / update of branch done
- [ ] PR to `master` branch (Product Owner / Scrum Master)
  - [ ] The [version](../dds_cli/version.py) is updated
    - [ ] I am bumping the major version (e.g. 1.x.x to 2.x.x)
      - [ ] I have made the corresponding changes to the API version

## Checks

- [ ] CodeQL passes
- [ ] Formatting: Black & Prettier checks pass
- Tests
  - [ ] I have added tests for the new code
  - [ ] The tests pass
