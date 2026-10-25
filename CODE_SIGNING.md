# Code signing policy

## Signature of the releases (minisign)

The files of a release for Windows (the installer and the portable zip) are
signed with [minisign](https://jedisct1.github.io/minisign/). The release
job of the CI (`.github/workflows/test.yml`, job `release`) signs them with
the project's key, checks each signature with the public key below and
publishes it next to the file as `<file>.minisig`; its trusted comment
names the file. The secret half of the key is a secret of the GitHub
environment `release` of this repository, and nowhere else in it: until it
is set there, the job signs nothing and publishes nothing.

The installed Windows program checks this signature before it runs an
update (`src/meridiana/updates.py`): it starts only the installer named
for the release's own version, whose SHA-256 is the one GitHub publishes
and whose signature, made with this key, names that very file. Any other
file is never started.

Public key (key id `CEFFF9269F08F845`):

    RWRF+AifJvn/zhz0o7MBObIYHgw9+sWoc4GaBK+qYnJY0AqeJm540y0a

To check a download by hand, with the `.minisig` of the release in the same
folder:

    minisign -Vm meridiana-setup-vX.Y.Z-windows-x64.exe -P RWRF+AifJvn/zhz0o7MBObIYHgw9+sWoc4GaBK+qYnJY0AqeJm540y0a

This is not an Authenticode signature: Windows does not know it, and
SmartScreen still warns when the installer is started from a download.

The Flatpak for Linux is not signed this way: it is built from the
manifest in `build-aux/flatpak/`, and its updates will come from the
desktop's software centre once a repository publishes it.

## Team roles

- Committers and reviewers: [Daniel Grasso](https://github.com/daniel-g-carrasco)
- Approvers: [Daniel Grasso](https://github.com/daniel-g-carrasco)

Every release is built by GitHub Actions from this repository, from the tag
of its version: the build scripts and the workflow are part of the
repository. Only the approver pushes a version's tag; the job that signs
builds nothing, it signs the files the build job made from that tag.

## Privacy policy

Meridiana sends nothing about its user anywhere, and the project files
never leave the computer. It asks four services for what they need to
answer, each with its switch in Preferences > Privacy:

- the address typed to find a site, to OpenStreetMap's Nominatim;
- the site's coordinates, to the European Commission's PVGIS (the weather
  of the typical year, the horizon, PVGIS's own estimate);
- the area in view, to the map server chosen under the plan;
- the Windows program, once a day at start, asks GitHub Releases
  (api.github.com) whether a newer version is out, sending nothing about
  the user or their files ("Updates" in Preferences > Privacy; Help >
  Check for updates asks at once).

Meridio, the assistant, answers with a model on the computer by default.
Only when the user chooses Claude in Preferences > Assistant, gives a key
and consents, do the questions and the project's figures they need go to
Anthropic's API; a project marked as reserved never goes there.
