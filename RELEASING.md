# Releasing pywb

## Release from main

1. Set `__version__` in `pywb/version.py` to the intended version, commit the
   change, and push it to `main`. This will automatically create a draft release.
2. Open the draft from the [GitHub releases page](https://github.com/webrecorder/pywb/releases).
3. Review the generated notes and update if needed.
4. If this is a beta release select **Pre-release**.
5. Click **Publish release**.
6. Check it appears on [PyPI](https://pypi.org/project/pywb/) 
   and [Docker Hub](https://hub.docker.com/r/webrecorder/pywb/tags). Check both
   publishing workflow runs for failures.

## Release from a branch (patch release)

1. Create and push a branch ending in `-release` from the appropriate existing
   release tag (for example, `2.10.1-release` from `v-2.10.0`).
2. Apply the patch changes on that branch.
3. Set `__version__` in `pywb/version.py` to the new version, commit, and push.
   This will create a draft release.
4. Open the draft from the [GitHub releases page](https://github.com/webrecorder/pywb/releases).
5. Review the generated notes and update if needed.
6. If this is a beta release select **Pre-release**.
7. Click **Publish release**.
8. Check it appears on [PyPI](https://pypi.org/project/pywb/) 
   and [Docker Hub](https://hub.docker.com/r/webrecorder/pywb/tags). Check both
   publishing workflow runs for failures.
