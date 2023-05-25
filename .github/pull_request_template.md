## Before submitting this PR

1. **Description:** _Add a summary of the changes in this PR and the related issue._
2. **Jira task / GitHub issue:** _Link to the github issue or add the Jira task ID here._
3. **How to test:** _Add information on how someone could manually test this functionality. As detailed as possible._
4. **Type of change:** [_Check the relevant boxes in the section below_](#what-type-of-changes-does-the-pr-contain)
5. **Add docstrings and comments to code**, _even if_ you personally think it's obvious.

## What _type of change(s)_ does the PR contain?

<!--
- "Breaking": The change will cause existing functionality to not work as expected.
- Workflow: E.g. a new github action or changes to this PR template. Anything that alters our or the codes workflow.
-->

- [ ] New feature
  - [ ] Breaking: _Please describe the reason for the break and how we can fix it._
  - [ ] Non-breaking
- [ ] Bug fix
  - [ ] Breaking: _Please describe the reason for the break and how we can fix it._
  - [ ] Non-breaking
- [ ] Security Alert fix
- [ ] Documentation
- [ ] Tests **(only)**
- [ ] Workflow

## Checklist

- [Sprintlog](../SPRINTLOG.md)
  - [ ] Added
  - [ ] Not needed (E.g. PR contains _only_ tests)
- Rebase / Update / Merge _from_ base branch (the branch from which the current is forked)
  - [ ] Done
  - [ ] Not needed
- Blocking PRs
  - [ ] Merged
  - [ ] No blocking PRs
- PR to `master` branch
  - [ ] Yes: Read [the release instructions](../docs/procedures/new_release.md)
    - [ ] I have followed steps 1-7.
  - [ ] No

## Actions / Scans

<!-- Go through all checkboxes. All actions must pass before merging is allowed.-->

- **Black**: Python code formatter. Does not execute. Only tests.
  Run `black .` locally to execute formatting.
  - [ ] Passed
- **Pylint**: Python code linter. Does not execute. Only tests.
  Fix code producing warnings. Code must get 10/10.
  - [ ] Warnings fixed
  - [ ] Passed
- **Prettier**: General code formatter. Our use case: MD and yaml mainly.
  Run `npx prettier --write .` locally to execute formatting.
  - [ ] Passed
- **Yamllint**: Linting of yaml files.
  - [ ] Passed
- **Tests**: Pytest to verify that functionality works as expected.
  - [ ] New tests added
  - [ ] No new tests
  - [ ] Passed
- **TestPyPi**: Build CLI and publish to TestPyPi in order to verify before release.
  - [ ] Passed
- **CodeQL**: Scan for security vulnerabilities, bugs, errors
  - [ ] New alerts: _Go through them and either fix, dismiss och ignore. Add reasoning in items below._
  - [ ] Alerts fixed: _What?_
  - [ ] Alerts ignored / dismissed: _Why?_
  - [ ] Passed
- **Trivy**: Security scanner
  - [ ] New alerts: _Go through them and either fix, dismiss och ignore. Add reasoning in items below._
  - [ ] Alerts fixed: _What?_
  - [ ] Alerts ignored / dismissed: _Why?_
  - [ ] Passed
- **Snyk**: Security scanner
  - [ ] New alerts: _Go through them and either fix, dismiss och ignore. Add reasoning in items below._
  - [ ] Alerts fixed: _What?_
  - [ ] Alerts ignored / dismissed: _Why?_
  - [ ] Passed
