# Security policy

Jamfbreak performs a real settings restore and should be used only on devices
the operator owns or is explicitly authorized to modify.

## Reporting a vulnerability

Please use this repository's private GitHub vulnerability-reporting or Security
Advisory feature. Do not include real device backups, UDIDs, serial numbers,
IMEIs, signing keys, certificates, or other personal data in a public issue.

## Release security

- Source releases intentionally exclude `jamfbreak/backups/`,
  `jamfbreak/bin/`, build output, and executable artifacts.
- Public binaries must be built from a clean checkout, Authenticode-signed,
  timestamped, and verified as described in `SIGNING.md`.
- CI runs `scripts/check_public_tree.py` and rejects tracked or first-commit
  candidate backups, helper binaries, signing keys, personal Windows paths,
  emails, and common tokens.
- A signature establishes publisher identity; it is not a warranty of zero
  data-loss, boot, compatibility, or antivirus risk.
