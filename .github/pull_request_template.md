> **Before submitting the PR, please go through the sections below and fill in what you can. If there are any items that are irrelevant for the current PR, remove the row. If a relevant option is missing, please add it as an item and add a PR comment informing that the new option should be included into this template.**

> **All _relevant_ items should be ticked before the PR is merged**

# Description

- [ ] Add a summary of the changes and the related issue
- [ ] Add motivation and context regarding why the change is needed
- [ ] List / describe any dependencies or other changes required for this change
- [ ] Fixes [link to issue / Jira issue ID]

## Type of change

- [ ] Documentation
- [ ] Workflow
- [ ] Security Alert fix
- [ ] Bug fix (non-breaking)
- [ ] New feature (non-breaking)
- [ ] Breaking change (breaking, will cause existing functionality to not work as expected)
- [ ] Tests (only)

# Checklist:

## General

- [ ] [Changelog](../CHANGELOG.md): New row added. Not needed when PR includes _only_ tests.
- [ ] Code change
  - [ ] Self-review of code done
  - [ ] Comments added, particularly in hard-to-understand areas
  - [ ] Documentation is updated

## Repository / Releases

- [ ] Blocking PRs have been merged
- [ ] Rebase / update of branch done
- [ ] PR to `master` branch (Product Owner / Scrum Master)
  - [ ] The [version](../dds_cli/version.py) is updated
    - [ ] I am bumping the major version (e.g. 1.x.x to 2.x.x)
      - [ ] I have made the corresponding changes to the API version

## Checks

- [ ] Formatting: Black & Prettier checks pass
- [ ] CodeQL passes
- [ ] Tests
  - [ ] I have added tests for the new code
  - [ ] The tests pass
