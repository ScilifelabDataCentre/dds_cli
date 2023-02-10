<!--
> **Before _submitting_ PR:**
>
> - Fill in and tick fields
> - _Remove all rows_ that are not relevant for the current PR
>   - Revelant option missing? Add it as an item and add a PR comment informing that the new option should be included into this template.
>
> **Before _merging_ PR:**
>
> _Tick all relevant items._
-->

## **1. This PR contains the following changes...**

_Add a summary of the changes and the related issue._

## **2. The following additional changes are required for this to work**

_Add information on additional changes required for the PR changes to work, both locally and in the deployments._

> E.g. Does the deployment setup need anything for this to work?

## **3. The PR fixes the following GitHub issue / Jira task**

<!-- Comment out the item which does not apply here.-->

- [ ] GitHub issue (link):
- [ ] Jira task (ID, `DDS-xxxx`):
- [ ] The PR does not fix a specific GitHub issue or Jira task

## **4. What _type of change(s)_ does the PR contain?**

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

## **5. Checklist**

<!-- Comment out the items which do not apply here.-->

### **Always**

<!-- Always go through the following items. -->

- [Changelog](../CHANGELOG.md)
  - [ ] Added
  - [ ] Not needed (E.g. PR contains _only_ tests)
- Rebase / Update / Merge _from_ base branch (the branch from which the current is forked)
  - [ ] Done
  - [ ] Not needed
- Blocking PRs
  - [ ] Merged
  - [ ] No blocking PRs
- PR to `master` branch
  - [ ] Yes: Go to the section [PR to master](#pr-to-master)
  - [ ] No

### If PR consists of **code change(s)**

<!-- If the PR contains code changes, the following need to be checked.-->

- Self review
  - [ ] Done
- Comments, docstrings, etc
  - [ ] Added / Updated
- Documentation
  - [ ] Updated
  - [ ] Update not needed

### If PR is to **master**

<!-- Is your PR to the master branch? The following items need to be checked off. -->

- [ ] I have followed steps 1-5 in [the release instructions](../docs/procedures/new_release.md)
- [ ] I am bumping the major version (e.g. 1.x.x to 2.x.x)
- [ ] I have made the corresponding changes to the web/API version

**Is this version _backward compatible?_**

- [ ] Yes: The code works together with `dds_web/master` branch
- [ ] No: The code **does not** entirely / at all work together with the `dds_web/master` branch. _Please add detailed and clear information about the broken features_

## **6. Actions / Scans**

<!-- Go through all checkboxes. All actions must pass before merging is allowed.-->

- **Black**: Python code formatter. Does not execute. Only tests.
  Run `black .` locally to execute formatting.
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
