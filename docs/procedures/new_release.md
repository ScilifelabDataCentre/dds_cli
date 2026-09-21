# How to create a new release

> ### Inform the users of an upcoming release
>
> Always inform users of an upcoming new release _at least_ a week prior to a new release:
>
> 1. Adding a "Message of the Day": `dds motd add`
> 2. Getting the MOTD ID: `dds motd ls`
> 3. Sending the MOTD to the users: `dds motd send [MOTD ID]`
>
> **Important**
>
> - If users do not upgrade the CLI when there is a new version, they may experience issues and errors.
> - If there is a major version mismatch between the API and CLI (e.g. API version 1.0.0 and CLI version 2.0.0 or vice versa), the DDS will inform the users that they are blocked from using the DDS until they have upgraded.
> - If there is no warning from the DDS and there is an error, the first thing they should do is verify that the `dds-cli` version is up to date

## Automatic Release Drafts

When changes are pushed to `dev` or `master`, a Draft Release is created/updated. The draft will be displayed here: https://github.com/ScilifelabDataCentre/dds_cli/releases. The draft will also have a suggestion for what the next version should be, based on PR labels.

## Go through these steps

1. Create a PR from `dev` to `master` and verify that the PRs included in the changes have the correct labels.

   > Check out the [Release Drafter config file](../../.github/release-drafter.yml) and/or the [PR template](../../.github/pull_request_template.md) for info on which code changes give which labels.

2. Check the release draft: Does the suggestion version seem appropriate? If not: Check the PRs and their labels, again.

   > **Note** that a _major version upgrade SHOULD NEVER BE DONE UNLESS THE API ALSO HAS THIS IDENTICAL CHANGE_

3. Fork a new branch from `dev`: `new-version_[new version]`
4. Update the version in [`version.py`](../../dds_cli/version.py)
5. Update the [changelog](../../CHANGELOG.rst) as follows:

   - Copy-paste the contents of the release draft into the top of the changelog
   - Follow the same structure/format as previous versions.
   - Patch changes, e.g. bug fix_: Patch version upgrade, e.g. `1.0.1 --> 1.0.2`
   - Minor changes, e.g. new feature_: Minor version upgrade, e.g. `1.1.0 --> 1.2.0`
   - Major [Breaking] changes or large new feature(s): Major version upgrade, e.g. `1.0.0 --> 2.0.0` SHOULD NEVER BE DONE UNLESS THE API ALSO HAS THIS IDENTICAL CHANGE.

6. Push your local `new-version_[new version]` branch to Github and create a PR.
7. Run the `rich-codex` action [here](https://github.com/ScilifelabDataCentre/dds_cli/actions/workflows/rich-codex-cli.yml); Choose the `new-version_[new version]` branch in the "Run workflow" drop-down button

> `rich-codex` will push changes to your branch; these commits _will not be signed_. In order for you to merge these changes into the `dev` branch, all commits need to be signed:
>
> 1.  Pull the changes to your local branch
> 2.  Run the following command. Git should start signing all commits in your PR.
>
>     ```bash
>     git rebase --exec 'git commit --amend --no-edit -n -S' dev
>     ```
>
> 3.  Force push the newly signed commits
>
>     ```bash
>     git push --force
>     ```

8. Verify that the new images look okay, then have the PR approved by another admin.
9. Go back to the PR from `dev` to `master` created in step 1.
   - Are you bumping the major version (e.g. 1.x.x to 2.x.x)?
     - Yes: Add this info to the PR.
   - Do the changes affect the backend API in any way?
     - Yes:
       - Add how the backend API is affected in the PR.
       - Make the corresponding changes to the backend API and create a PR _before_ you merge this PR.
       - _Backward compatibility:_ Check whether or not the dds_cli master branch works with the code in the backend PR. Check if the dds_web changes work with the previous version of the dds_cli. If something might break - give detailed information about what. **The users should be informed of this, e.g. via a MOTD.**
   - All changes should be approved in the PRs to dev so reviewing the changes a second time in this PR is not necessary. Instead, the team should look through the code just to see if something looks weird.
   - All sections and checks in the PR template should be filled in and checked. Follow the instruction in the PR description field.
   - There should be at least one approval of the PR.
   - If everything looks ok and there's at least one approval, this PR can be merged into `master`.

10. [Check and edit the auto-generated release draft](https://github.com/ScilifelabDataCentre/dds_cli/releases)

    - 1. `Choose a tag` &rarr; `Find or create a new tag` &rarr; Fill in the new version, e.g. if the new version is `1.0.0`, you should fill in `v1.0.0`.
    - 2. `Target` should be set to **`master`**
    - 3. `Release title` field should be set to the same as the tag, e.g. `v1.0.0`

11. [Publish the Release Draft](https://github.com/ScilifelabDataCentre/dds_cli/releases)

    > A new version of the CLI will be published to [PyPi](https://pypi.org/project/dds-cli/)

12. Inform users (`dds-status` Slack channel) and relevant IT departments / HPC centers about new version. Create MOTD, send the MOTD when minor or major changes.

> **NAISS**
>
> There is no automatic upgrade of the `dds-cli` on NAISS resources other than UPPMAX and we need to inform them via email every time there is a new version.
>
> ```
> [Recipient]: support@naiss.se
> [Subject]: Uppgrade dds-cli module
>
> [Message]:
> Hi,
>
> There is a new version of the dds-cli. Could you please upgrade the version to [new dds-cli version] on all relevant NAISS clusters/systems?
>
> Thank you in advance!
> ```
>
> If there are breaking changes, PDC should be informed in advance. See the Uppmax email below as a template, but change it accordingly.

> **UPPMAX**
>
> Uppmax automatically upgrades the `dds-cli` version every day at midnight.
> If there has been a major version change though and the CLI contains breaking changes, _Uppmax should be notified well in advance_ in order to plan for an upgrade at a specific time so that the users are blocked (automatic functionality in dds_web) for as short time as possible.
>
> ```
> [Recipient]: support@uppmax.uu.se
> [Subject]: Upgrade dds-cli module
>
> [Message]:
> Hi,
>
> We will be releasing a new major version of the dds-cli on <Day Date Time>. The changes are breaking - would it be possible for you do a manual version upgrade at that time, so that the users don't experience issues?
>
> Thank you in advance!
> ```
