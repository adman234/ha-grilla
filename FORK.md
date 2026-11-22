# About this fork

This is a personal fork of [zwrose/ha-grilla](https://github.com/zwrose/ha-grilla).
`main` here is upstream plus every feature below. Each feature also lives on its
own branch, based on upstream, so it can go upstream as a separate pull request.

Fork-only files (this one and `docs/fork/`) never go into feature branches, so
they can't leak into upstream PRs.

## Branches

| Branch | Purpose | Upstream PR |
|---|---|---|
| `main` | Upstream + all merged features + fork notes. What HACS installs from this fork. | Never |
| `fix/silverbac-probe2` | Hide the probe 2 entities on models without a second probe ([upstream #37](https://github.com/zwrose/ha-grilla/issues/37)). | Yes |
| `feat/heartbeat` | Send the app's 15 s heartbeat so the grill keeps streaming without the app open. | Yes |
| `feat/remote-control` | Power off button and target temperature control. | Yes, after discussion |
| `fix/misc` | Other bugs found during review. | Yes |

Status: all four branches are done, tested, and merged into `main`. None has
been pushed or offered upstream yet. The heartbeat and remote-control commands
haven't been tried on a real grill. See
[docs/fork/protocol-notes.md](docs/fork/protocol-notes.md) for the research
behind them.

## Rules that keep upstream merges easy

1. **Branch every feature from `upstream/main`, never from fork `main`.** Then
   each branch holds only its own change and makes a clean PR.
2. **Fork `main` only receives merges.** Don't commit code directly to `main`.
   Merge feature branches in, and merge `upstream/main` in. The one exception is
   the fork-only docs.
3. **Keep features small and separate.** Each feature should touch as few
   upstream files as possible, with new code in new files where practical.
4. **Use Conventional Commits** (see `CONTRIBUTING.md`). Upstream squash-merges
   by PR title.

## Workflows

One-time setup after cloning:

```sh
git remote add upstream https://github.com/zwrose/ha-grilla.git
```

Pull in upstream changes:

```sh
git fetch upstream
git checkout main && git merge upstream/main          # fork main
git checkout feat/heartbeat && git rebase upstream/main  # each unmerged feature branch
git push --force-with-lease origin feat/heartbeat
```

Land a feature on fork `main`:

```sh
git checkout main && git merge --no-ff feat/heartbeat && git push
```

After upstream accepts a feature, delete its branch. The next `git merge
upstream/main` brings the squashed upstream version, and Git resolves it
against the earlier merge.

## Dependency on aiogrilla

The integration talks to the grill through the
[aiogrilla](https://github.com/zwrose/aiogrilla) library, which
`manifest.json` pins as `aiogrilla>=0.2.4`. The **heartbeat** and **remote
control** features need changes in that library (publishing to MQTT and
calling the PowerDown API). Before coding those, choose one:

- fork aiogrilla too, and point `manifest.json` at the fork with a
  `git+https://...` requirement on fork `main` only; or
- add the code inside this integration first, and move it into aiogrilla
  in the upstream PR.

**Chosen: fork aiogrilla.** The clone has `feat/heartbeat` and
`feat/remote-control` branches (from aiogrilla `upstream/main`) and a fork
`main` that merges both and sets the version to `0.2.5.dev1`. Fork `main` here
pins that build in `manifest.json` as
`git+https://github.com/adman234/aiogrilla@<sha>#aiogrilla==0.2.5.dev1`. Keep
the `#aiogrilla==<version>` fragment: without it Home Assistant either keeps an
installed 0.2.4 or reinstalls from GitHub on every start. When you change the
aiogrilla fork, bump its dev version and update the sha and version here.
The ha-grilla feature branches keep `aiogrilla>=0.2.4`; their upstream PRs wait
for an aiogrilla release with these calls.

The probe 2 fix and misc bug fixes need only this repository.
