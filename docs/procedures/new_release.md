# How to create a new release

1. Create a PR from `dev` to `master`: "New release". Use this for step 3.
2. Fork a new branch from `dev`: "New version & changelog"
3. Update the version [changelog](../../CHANGELOG.rst)

   **Tip:** Use the PR to `master` (step 1) to see all changes since last release.

   - The new version should be at the top of the page
   - List the changes that the users will / may notice
   - Do not add information regarding workflow (e.g. GitHub Actions) etc

4. Update the version in [`version.py`](../../dds_cli/version.py)

   - _Minor changes, e.g. bug fix_: Minor version upgrade, e.g. `1.0.1 --> 1.0.2`
   - _Small changes, e.g. new feature_: Mid version upgrade, e.g. `1.1.0 --> 1.2.0`
   - _Breaking changes or large new feature(s)_: Major version upgrade, e.g. `1.0.0 --> 2.0.0` _SHOULD NEVER BE DONE UNLESS THE API ALSO HAS THIS IDENTICAL CHANGE._

     > Will break if Web / API version not bumped as well

5. Push changelog and version change to branch
6. Run the `rich-codex` action [here](https://github.com/ScilifelabDataCentre/dds_cli/actions/workflows/rich-codex-cli.yml); Choose your current branch where it says "Run workflow"
   - `rich-codex` will push changes to your branch; these commits _will not be signed_
   - In order for you to merge these changes into the `dev` branch, all commits need to be signed:
     1. Pull the changes to your local branch
     2. Run the following command:
        ```bash
        git rebase --exec 'git commit --amend --no-edit -n -S' dev
        ```
        Git should now be signing all commits in this PR.
     3. Force push the newly signed commits
        ```bash
        git push --force
        ```
7. Create a new PR from `<your-branch>` to `dev`
   1. Verify that the new code example images look ok
   2. Wait for approval and merge by Product Owner or admin
8. Create a PR from `dev` to `master`

   - Are you bumping the major version (e.g. 1.x.x to 2.x.x)?
     - Yes: Add this info to the PR.
   - Do the changes affect the API in any way?
     - Yes:
       - Add how the API is affected in the PR.
       - Make the corresponding changes to the API and create a PR _before_ you merge this PR.
   - _Backward compatibility:_ Check whether or not the dds_cli master branch works with the code in the PR. Note if the dds_web changes work with the previous version of the dds_cli. If something might break - give detailed information about what. **The users should be informed of this, e.g. via a MOTD.**
   - All changes should be approved in the PRs to dev so reviewing the changes a second time in this PR is not necessary. Instead, the team should look through the code just to see if something looks weird.
   - All sections and checks in the PR template should be filled in and checked. Follow the instruction in the PR description field.
   - There should be at least one approval of the PR.
   - _Everything looks ok and there's at least one approval?_ Merge it.

   > Documentation changes are automatically updated on GitHub pages when there's a push to `master`. However, in order to keep things consistent and to avoid confusion with the versions, always release a new version when changes are pushed to `master` (assuming all the changes have been verified)

9. [Draft a new release](https://github.com/ScilifelabDataCentre/dds_cli/releases)

   1. `Choose a tag` &rarr; `Find or create a new tag` &rarr; Fill in the new version, e.g. if the new version is `1.0.0`, you should fill in `v1.0.0`.
   2. `Target` should be set to `master`
   3. `Release title` field should be set to the same as the tag, e.g. `v1.0.0`
   4. `Write` &rarr; `Generate release notes`.

      You can also fill in something to describe what has been changed in this release, if you feel that the auto-generated release notes are missing something etc.

   5. `Publish release`.

      A new version of the CLI will be published to [PyPi](https://pypi.org/project/dds-cli/)

10. Verify that the new CLI version is updated on Uppmax

    Uppmax automatically upgrades the `dds-cli` version every day at midnight. Double-check that this has worked, if you have an Uppmax account.

    If there has been a major version change though and the CLI contains breaking changes, _Uppmax should be notified well in advance_ in order to plan for an upgrade at a specific time so that the users are blocked (automatic functionality in dds_web) for as short time as possible.

    ```
    [Recipient]: support@uppmax.uu.se
    [Subject]: (Pavlin Mitev) Upgrade dds-cli module

    [Message]:
    Hi,

    We will be releasing a new major version of the dds-cli on <Day Date Time>. The changes are breaking - would it be possible for you do a manual version upgrade at that time, so that the users don't experience issues?

    Thank you in advance!
    ```

11. Inform users that there is a new version by adding a Message of the Day: `dds motd add`

- If users do not upgrade the CLI when there is a new version, they may experience issues and errors.
- If there is a major version mismatch between the API and CLI (e.g. API version 1.0.0 and CLI version 2.0.0 or vice versa), the DDS will inform the users that they are blocked from using the DDS until they have upgraded.
- If there is no warning from the DDS and there is an error, the first thing they are asked to do in the troubleshooting documentation is to verify that the CLI version is correct.

> Possible to have a procedure where we notify via email when there is a major version bump but only use the MOTD functionality if the version bump is mid / minor, but updating everytime we release a new version will only lead to the users ignoring the emails and therefore not getting the truly important information when they actually need it.
