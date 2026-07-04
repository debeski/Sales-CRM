# Releasing Switch POS

The app ships as the Docker image **`debeski/sales`**. Releases are **tag-driven**:
pushing a `v*` git tag runs `.github/workflows/release.yml`, which builds the
multi-arch image, pushes it to Docker Hub, and creates a GitHub Release. The
`VERSION` file is the single source of truth for the version.

## One-time setup

Add two repository **Secrets** (Settings → Secrets and variables → Actions → *Secrets* tab):

| Secret | Value |
| :--- | :--- |
| `DOCKERHUB_USERNAME` | Docker Hub namespace that owns the image (`debeski`). |
| `DOCKERHUB_TOKEN` | Docker Hub **access token** with read/write on `debeski/sales` (Docker Hub → Account Settings → Personal access tokens). |

> The token must be a **Secret**, not a *Variable* — Variables are printed in build logs.

## Cutting a release

1. Update `CHANGELOG.md`: add a new `## vX.Y.Z` section at the top describing the
   changes. The release notes are extracted from this exact section.
2. Bump `VERSION` to the same `X.Y.Z` (no `v` prefix). The workflow **fails** if
   the tag and `VERSION` disagree.
3. Commit both on `main`.
4. Tag and push:

   ```bash
   git tag -a vX.Y.Z -m "vX.Y.Z" && git push origin vX.Y.Z
   ```

The `Release` workflow then:

- verifies `tag == VERSION`,
- resolves the baked DjangoLux version from the pinned `django-lux[updater]==` in
  `requirements.txt` and passes it as `--build-arg DLUX_BAKED_VERSION` (stamped as
  `LABEL org.switchlibya.dlux_baked_version` — the composer-updater version gate),
- runs `scripts/smoke-test.sh` against a freshly built image (boots the app and
  applies all migrations on SQLite — gates the push on a working image),
- builds `linux/amd64` + `linux/arm64` with Buildx,
- pushes `debeski/sales:X.Y.Z` and `debeski/sales:latest`,
- publishes the GitHub Release using the matching `CHANGELOG.md` section.

## Deploying the published image

The production `compose.yml` reads `${WEB_IMAGE:-switch_pos:latest}`. To run the
released image instead of building locally:

```bash
WEB_IMAGE=debeski/sales:latest ./start.sh -d        # or a pinned :X.Y.Z
```

## CI

`.github/workflows/ci.yml` runs on every push/PR to `main`: runs Django's system
checks and the test suite (`config.settings_dev_sqlite`, no DB/Redis needed), and
builds the Docker image (no push) + runtime smoke test to catch `Dockerfile`
breakage before a release.

## Why a tag shows under "Tags" but not "Releases"

A git tag is just a commit pointer; a GitHub **Release** is a separate object
layered on a tag. Pushing a tag never auto-creates a Release — `release.yml` does
that for `v*` tags. (Manually: Releases → *Draft a new release* → pick the tag.)
