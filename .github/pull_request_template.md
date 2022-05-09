# Description

Please include the following in this section

- [ ] Summary of the changes and the related issue
- [ ] Relevant motivation and context
- [ ] Any dependencies that are required for this change

Fixes # (issue)

## Type of change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] This change requires a documentation update

# Checklist:

Please delete options that are not relevant.

- [ ] Any dependent changes have been merged and published in downstream modules
- [ ] Rebase/merge the branch which this PR is made to
- [ ] Product Owner / Scrum Master: This PR is made to the `master` branch and I have updated the [version](../dds_cli/version.py)

## Formatting and documentation

- [ ] I have added a row in the [changelog](../CHANGELOG.md)
- [ ] The code follows the style guidelines of this project: Black / Prettier formatting
- [ ] I have performed a self-review of my code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings

## Tests

- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes


Additional checks before submitting a PR to the `master` branch:
- Change version in `dds_cli/version.py` (?) 