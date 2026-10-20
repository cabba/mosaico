---
title: Release Cycle
position: 1
description: "Mosaico's monorepo branching strategy, semantic versioning policy, and release process for mosaicod and the SDK. Covers the relationship between daemon and SDK versions and how breaking changes are communicated."
---

## Monorepo

Mosaico uses a monorepo that holds `mosaicod`, the SDK and the documentation. All development happens on `main`, and every release of every component is cut from the same release branch.

## Versioning

The `major.minor` pair is set by `mosaicod`, and the SDK shares it with the server.

### mosaicod

`mosaicod` follows strict [semantic versioning](https://semver.org) in the form `vX.Y.Z`. A new `major.minor` defines the protocol contract that the SDK targets.

Mosaico is currently in a pre-1.0 phase and follows the `0.Y.Z` convention of semantic versioning. A major version of `0` marks initial development: the public API is not yet considered stable and can change between minor versions. During this phase:

- `Y` (minor) is incremented by every milestone, moving `mosaicod` from `0.Y` to `0.(Y+1)`, and may include breaking changes.
- `Z` (patch) only contains backward compatible fixes.

Version `1.0.0` will mark the first stable API. From then on, breaking changes will require a new major version.

The backend migration required for each new `Y` is documented in the dedicated migration section of the documentation.

### SDK

The SDK does not follow semantic versioning. It uses the form `X.Y.N`:

- `X.Y` is the `major.minor` of the server the SDK targets.
- `N` is an incremental number chosen by the SDK maintainers.

The SDK can introduce new features between two incremental versions, but every `X.Y.N` release must keep the contract with `mosaicod X.Y`.

Breaking changes on the client side are never shipped in an incremental release. They follow the server releases and land in the SDK `X.Y.0` of the first available `mosaicod` release.

The `N` of an SDK is not a patch number and is not aligned with the `Z` of the server. For example, SDK `0.8.4` and `mosaicod 0.8.1` are compatible because they share `0.8`.

## Branches

### `main`

The only development branch. All finished work lands here via pull request, for the daemon, the SDK and the documentation. The version on `main` is always a `-dev` snapshot (e.g. `v0.8.0-dev`) and is never released directly. `main` must be in a releasable state at all times: every merged PR leaves it buildable, tested and ready to be cut into a release branch.

### `issue/<num>`

Short-lived branches for a single feature or bug fix. Always branched from `main`, merged back via PR, then deleted.

Documentation ships with the code it describes. Every issue that changes a behavior, an API or a configuration includes the matching documentation changes in the same branch, so code and documentation are merged, backported and released together.

### `release/vX.Y`

One release branch per `major.minor`, cut from `main`. It is the single backport target for that version: the daemon, the SDK and the documentation are all released from it. Changes usually arrive as backports from `main`.

Keeping every component on one branch simplifies backports for a given release and minimizes misalignment between the server, the SDK and the docs.

## Release

`mosaicod` is released frequently: every major feature completed on `main` triggers a new `major.minor` release. Major features are tracked as parent issues carrying the `Milestone` label. This shortens the release cycle and gives the SDK more room to ship new features.

### Cut the release branch

When `main` is ready, `release/vX.Y` is cut from it and two version bumps happen at the same time:

- `main`: every component advances to `vX.(Y+1).0-dev`, opening the next development cycle.
- `release/vX.Y`: `mosaicod` and the SDK are set to `vX.Y.0-rc`.

### Release candidates

There are no release candidate tags. The release candidate is the state of `release/vX.Y` while its version carries the `-rc` suffix.

### Promote to stable

Change the version from `vX.Y.Z-rc` to `vX.Y.Z` and tag the commit on `release/vX.Y`. CI/CD produces the final release artifacts for that component.

### Daemon patch releases

Backport the fix from `main` to `release/vX.Y`, increment `Z` and tag the commit.

### SDK incremental releases

Backport the change from `main` to `release/vX.Y`, increment `N` and tag the commit. An incremental release can contain bug fixes or new features, as long as it keeps the contract with `mosaicod X.Y`.

## Backports

Changes usually reach `release/vX.Y` as backports from `main`. When it makes sense, a change can also be developed directly on the release branch.

- A fix can be backported to any maintained `release/vX.Y` where it applies.
- An SDK feature can be backported to `release/vX.Y` only if it works against `mosaicod X.Y`. If it depends on server functionality introduced after `X.Y`, it stays on `main` and ships with the next SDK `X.(Y+1).0`.

## Tags

All tags are created on `release/vX.Y`.

| Component | Tag format | Notes |
| --- | --- | --- |
| Daemon | `vX.Y.Z` | Triggers binary and container builds |
| Python SDK | `py/vX.Y.N` | Triggers PyPI publish and SDK artifacts |
| Documentation | `doc/vX.Y` (lightweight) | Rolled forward on each update; triggers a docs deployment |
