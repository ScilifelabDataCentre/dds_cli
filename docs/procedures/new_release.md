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
5. Update the [changelog](../../CHANGELOG.rst).

   > Copy-paste the contents of the release draft into the top of the changelog; Follow the same structure/format as previous versions.

6. Push the changelog and version to the `new-version_[new version]` branch
7. Run the `rich-codex` action [here](https://github.com/ScilifelabDataCentre/dds_cli/actions/workflows/rich-codex-cli.yml); Choose the `new-version_[new version]` branch in the "Run workflow" drop-down button

   > `rich-codex` will push changes to your branch; these commits _will not be signed_. In order for you to merge these changes into the `dev` branch, all commits need to be signed:
   >
   > 1. Pull the changes to your local branch
   > 2. Run the following command. Git should start signing all commits in your PR.
   >
   >    ```bash
   >    git rebase --exec 'git commit --amend --no-edit -n -S' dev
   >    ```
   >
   > 3. Force push the newly signed commits
   >
   >    ```bash
   >    git push --force
   >    ```

8. Create a new PR from `new-version_[new version]` to `dev`, and verify that the new images look OK.
9. Create a PR from `dev` to `master`

   > **Do the changes affect the API in any way?**
   > If yes:
   >
   > - Add how the API is affected in the PR.
   > - Make the corresponding changes to the API and create a PR _before_ you merge this PR.
   >
   > **Re: Documentation and pushes to `master`**
   > Documentation changes are automatically updated on GitHub pages when there's a push to `master`. However, in order to keep things consistent and to avoid confusion with the versions, always release a new version when changes are pushed to `master` (assuming all the changes have been verified)
   >
   > **Re: PR approval**
   >
   > - All changes should be approved in the PRs to dev so reviewing the changes a second time in this PR is not necessary.Instead, the team should look through the code just to see if something looks weird.
   > - When there's at least one approval: Merge it.

10. [Publish the Release Draft](https://github.com/ScilifelabDataCentre/dds_cli/releases)

    > A new version of the CLI will be published to [PyPi](https://pypi.org/project/dds-cli/)

11. Inform users (`dds-status` Slack channel) and relevant IT departments / HPC centers about new version

> **Uppmax**
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
