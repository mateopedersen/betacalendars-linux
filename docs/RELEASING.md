# Releasing

The release workflow builds the Snap on Ubuntu, runs the Python checks and GTK screenshot capture, and publishes the tested revision to `latest/candidate` when store credentials are configured. It does not release to stable automatically.

## Snap Store credential for GitHub Actions

After registering `betacalendars` in the Snap Store, create a restricted credential from an authenticated Snapcraft CLI session:

```sh
snapcraft export-login --snaps=betacalendars \
  --channels=latest/candidate,latest/stable \
  --acls=package_access,package_push,package_update,package_release \
  snapcraft-store-login.txt
```

Copy the file contents directly into the GitHub repository secret named `STORE_LOGIN`. Do not commit the file or print its contents. Enable candidate automation with the repository variable `ENABLE_SNAP_PUBLISH=true`. The credential can be revoked after release or re-exported with an expiration date.

## Stable release

Review the candidate revision on a Linux desktop, including the month and year views, designer export, CLI, and confinement behavior. Then promote that same candidate revision to `latest/stable` in the Snap Store dashboard. Verify the public listing, metadata, screenshots, and rendered links after the stable channel is live.

## Release checklist

- Confirm the tag matches the application version.
- Confirm CI, Python distribution, AppStream metadata, and Snap build pass.
- Test the candidate GUI and CLI under strict confinement.
- Confirm there are no AppArmor denials or unexpected interface requests.
- Promote the tested revision to stable and verify the public Store page.
