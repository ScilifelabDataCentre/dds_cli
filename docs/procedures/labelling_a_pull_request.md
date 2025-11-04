# Options when labelling your Pull Request

On the right hand side of your PR, there's a section called `Labels`. From the table below, choose the (**one**) label that describes the changes in your PR the best. You can use multiple labels, but only one of the labels mentioned in this file. For example, you can use `skip-changelog` and `tests`, but not `skip-changelog` and `type: breaking`.

| Label             | Description                                                                                                                                                                                    |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `skip-changelog`  | The change is irrelevant for the end-users, e.g. the change includes changes in GitHub Actions, the PR contains tests _only_, etc. PRs with this label will not be displayed in release notes. |
| `type:breaking`   | Changes in the PR will cause existing functionality to stop working as expected. The master branch of the API will no longer work with the CLI dev branch (and vice versa).                    |
| `type:feature`    | You've added new functionality or updated an existing one. This includes database changes (in most cases). Ask if you're unsure.                                                               |
| `type:bug`        | The PR fixes a bug.                                                                                                                                                                            |
| `type:docs`       | The PR _only_ updates documentation.                                                                                                                                                           |
| `type:dependency` | You've updated a dependency version, e.g. a Python package in requirements.                                                                                                                    |
