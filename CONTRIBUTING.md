# Contributing

## Getting started

Please have a look at: <https://github.com/cobbler/cobbler/wiki>

The Github Wiki should be the place for developers to document with a single page a single topic about developing
cobbler.

## Pull Requests

The following roles exist in the context of a Pull Request:

- Creator
- Reviewer
- Collaborators

The guidelines noted here describe the expectations that should be met when submitting a Pull request.

### Pull Request Creators

1. Please fill out the Pull Request template.
2. Please provide a description for someone not familiar with your code changes to be still able to understand your changes in the context of the project.
3. Please enable the reviewer with the provided information in the description to understand the PR without opening any external resources like bug reports.
4. Please ensure that before hitting the "Create" button on GitHub you have read and understood the `CONTRIBUTING.md` and linked GitHub Wiki pages.
5. Please ensure all automation on GitHub receives a positive result checkmark.
6. Please state in a comment why a negative result - if occurring - is incorrect or not your fault.
7. Please use the GitHub functionality of re-requesting a review in case you haven't gotten a review after a reasonable time.
8. Please re-request a review in case you made substantial changes to the Pull Request.
9. Please write detailed and meaningful commit messages. Avoid the usage of generic messages like "fix bug". Further information can be found here:
    - https://cbea.ms/git-commit/
    - https://www.freecodecamp.org/news/how-to-write-better-git-commit-messages/

### Pull Request Reviewers

As a Pull Request Reviewer, the most important point is that the Creator is following the points above. In the case that there are things that haven't been followed please kindly ask the Creator to change that. This should also be done for the rest of the contributing guidelines in this document.

Once the points above are fulfilled there are a number of things that should be taken care of:

1. Check that the style guides that cannot be automatically enforced, are fulfilled.
2. Verify that the description of the Pull Request matches the code that was submitted.
3. Check that the submitted changes make sense in the context of the project and branch. A not acceptable example would be a feature backport after the target branch was already declared end of life.
4. Verify that the new and modified test cases are useful to the codebase.
5. Check that you can understand the code. If you don't understand it the likelihood of a required change is almost given.

Optionally you additionally do the following things as well:

1. If you have a better or different approach to fix the problem, please feel free to point it out. The suggestions shouldn't cause the PR to not be merged.
2. If you have informal comments or nitpicks, please submit them as early as possible and mark them as such accordingly. Informal comments and nitpicks shouldn't cause the PR to not be merged.

Very important during the whole process is that a reviewer should encourage more contributions by the author. Good things should be highlighted and should make the Pull Request Creator feel appraised.

Finally, if your review is completed and all required suggestions have been followed, please provide approval so PR can be merged.

Use these guidelines, but feel free to go beyond the points listed here if you have the capacity.

### Pull Request Collaborators

Please communicate respectfully with each another. So far no extra guidelines have been created for Collaborators.
