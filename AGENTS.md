# SPA contributor instructions

Work in the directory assigned by your issue. Coordinate changes to `docs/contracts.md` in a pull request before relying on a new contract. Use fixtures to build independently while other services are in progress. Never commit signing secrets or claim simulated values are confirmed ledger values.

## Branch workflow

1. Fetch and pull the latest `main` before creating a feature branch.
2. Make a branch named `feat/<issue>-<short-name>` or `fix/<issue>-<short-name>`. Do not push directly to `main`.
3. Before **every push**, fetch and integrate changes that teammates have pushed. Run `git fetch origin`, then `git pull --rebase origin <your-branch>` if your feature branch already exists remotely. Run `git rebase origin/main` so your branch includes the latest main. Resolve conflicts locally and rerun the relevant checks. If the remote feature branch is new, skip the branch pull and rebase onto `origin/main`.
4. Push the branch with `git push -u origin HEAD` for its first push, then `git push`. After rebasing an already pushed branch, use `git push --force-with-lease` only on your own feature branch. Never force push `main` or another teammate's branch.
5. Open a PR that links the issue. Enable auto-merge. GitHub must report a mergeable branch and passing required CI before merging. Update and recheck when main changes.

Run the commands in `TESTING.md` before a push. Add meaningful tests for each behavior you implement. The policy gateway, not the agent explanation, decides whether money can move.
