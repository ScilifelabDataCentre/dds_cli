## Pull Request Template

### Before Marking as Ready for Review

- [ ] Add relevant information to the sections below ([Summary](#summary) etc)
- [ ] Rebase or merge the latest `dev` (or other targeted branch)
- [ ] Update documentation if needed
- [ ] Add an entry to the [`SPRINTLOG.md`](https://github.com/ScilifelabDataCentre/dds_cli/blob/dev/SPRINTLOG.md) if needed
- [ ] Choose an appropriate label. See [here](https://github.com/ScilifelabDataCentre/dds_cli/blob/dev/docs/procedures/labelling_a_pull_request.md) for information on the labelling options
- [ ] The code follows the [style guidelines](https://github.com/ScilifelabDataCentre/dds_cli/blob/dev/docs/procedures/style_guidelines.md)
- [ ] Perform a self-review: read the diff as if reviewing someone else's code
- [ ] I have commented the code, particularly in hard-to-understand areas
- [ ] Verify that all checks and tests have passed

**If the target branch is `master`**:

- [ ] Read and follow [the release instructions](https://github.com/ScilifelabDataCentre/dds_cli/blob/dev/docs/procedures/new_release.md)

### Summary

_Describe what the PR changes and why._

### Related Issue/Ticket

_Link GitHub issue or provide Jira ID._

### Testing

_If applicable: How did you verify the change? Include commands, data, or screenshots._

### Reviewer Notes

_Anything that helps reviewers (e.g. areas needing close attention)._

---

Once all boxes are checked, mark the PR as **Ready for Review** and tag at least one team member as the initial reviewer.


## 5. Actions / Scans

**Make sure that the following checks/actions have passed.**

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
