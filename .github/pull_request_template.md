## Read this before submitting the PR

1. Always create a Draft PR first
2. Go through sections 1-5 below, fill them in and check all the boxes
3. Make sure that the branch is updated; if there's an "Update branch" button at the bottom of the PR, rebase or update branch.
4. When all boxes are checked, information is filled in, and the branch is updated: mark as Ready For Review and tag reviewers (top right)
5. Once there is a submitted review, implement the suggestions (if reasonable, otherwise discuss) and request an new review.

If there is a field which you are unsure about, enter the edit mode of this description or go to the [PR template](../.github/pull_request_template.md); There are invisible comments providing descriptions which may be of help.

## 1. Description / Summary

**Add a summary here**: What does this PR add/change and why?

## 2. Jira task / GitHub issue

**Is this a GitHub issue?** --> Add the link to the github issue

**Is this from a Jira task?** --> If your branch does not contain info regarding the Jira task ID, put it here.

## 3. Type of change - Add label

**What _type of change(s)_ does the PR contain? For an explanation of the different options below, enter edit mode of this PR description template.**

- `type: breaking`: Changes in this PR will cause existing functionality to not work as expected. The master branch of the API will no longer work with the CLI dev branch (and vice versa).
- `type: feature`: You've added new functionality or updated an existing one.
- `type: bug`: The PR fixes a bug. 
- `type: docs`: The PR _only_ updates documentation. 
- `type: dependency`: You've updated a dependency version, e.g. a python package (in requirements.txt).
- `skip-changelog`: None of the above mentioned labels fit in. E.g. a new GitHub Action, a PR containing _only_ tests, etc.

## 4. Additional information

- [ ] I have added an entry to the [Sprintlog](../SPRINTLOG.md) <!-- Add a row at the bottom of the SPRINTLOG.md file (not needed if PR contains only tests). Follow the format of previous rows. If the PR is the first in a new sprint, add a new sprint header row (follow the format of previous sprints). -->
- [ ] This is a PR to the `master` branch: _If checked, read [the release instructions](../doc/procedures/new_release.md)_ <!-- Check this if the PR is made to the `master` branch. Only the `dev` branch should be doing this. -->
  - [ ] I have followed steps 1-8. <!-- Should be checked if the "PR to `master` branch" box is checked AND the specified steps in the release instructions have been followed. -->

## 5. Actions / Scans

**Make sure that the following checks/actions have passed.**

- **Black**
<!--
  What: Python code formatter.
  How to fix: Run `black .` locally to execute formatting.
-->
- **Prettier**
<!--
  What: General code formatter. Our use case: MD and yaml mainly.
  How to fix: Run npx prettier --write . locally to execute formatting.
-->
- **Pylint**
<!--
  What: Python code linter.
  How to fix: Manually fix the code producing warnings. Code must get 10/10.
-->
- **Yamllint**
<!--
  What: Linting of yaml files.
  How to fix: Manually fix any errors locally.
-->
- **Tests**
<!--
  What: Pytest to verify that functionality works as expected.
  How to fix: Manually fix any errors locally. Follow the instructions in the "Run tests" section of the README.md to run the tests locally.
  Additional info: The PR should ALWAYS include new tests or fixed tests when there are code changes. When pytest action has finished, it will post a codecov report; Look at this report and verify the files you have changed are listed. "90% <100.00%> (+0.8%)" means "Tests cover 90% of the changed file, <100 % of this PR's code changes are tested>, and (the code changes and added tests increased the overall test coverage with 0.8%)
-->
- **CodeQL**
<!--
  What: Scan for security vulnerabilities, bugs, errors.
  How to fix: Go through the alerts and either manually fix, dismiss or ignore. Add info on ignored or dismissed alerts.
-->
- **Trivy**
<!--
  What: Security scanner.
  How to fix: Go through the alerts and either manually fix, dismiss or ignore. Add info on ignored or dismissed alerts.
-->
- **Snyk**
<!--
  What: Security scanner.
  How to fix: Go through the alerts and either manually fix, dismiss or ignore. Add info on ignored or dismissed alerts.
-->
- **TestPyPI**
<!--
  What: Builds the CLI and publishes to TestPyPI in order to verify before release.
  How to fix: Check the action logs and fix potential issues manually.
-->

If an action does not pass and you need help with how to solve it, enter edit mode of this PR template or go to the [PR template](../.github/pull_request_template.md).
