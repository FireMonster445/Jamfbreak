# Signing Jamfbreak for Windows

Code signing identifies the publisher and allows reputation to accumulate. It
does not guarantee that SmartScreen or every antivirus engine will allow a new
release. Never weaken antivirus settings, obfuscate the program, or ask users
to create exclusions.

## Recommended release path

1. Build only from a clean Git checkout. The release specification does not
   include `bin/`, `backups/`, `build/`, or previous `dist/` content.
2. Obtain a public-trust signing identity:
   - Publish through the Microsoft Store, or
   - use [Microsoft Artifact Signing](https://learn.microsoft.com/azure/artifact-signing/quickstart)
     if your individual/organization and region are eligible, or
   - obtain an OV code-signing certificate from a trusted certificate authority.
3. Sign the final EXE exactly once and apply an RFC 3161 timestamp.
4. Verify the Authenticode signature and calculate the SHA-256 hash.
5. Upload only the verified signed file. Never modify it after signing.

Microsoft's current SmartScreen guidance explains that even a valid OV/EV
signature can initially show an unrecognized-app warning while reputation is
new. EV no longer automatically bypasses that warning:
[SmartScreen reputation for app developers](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation).

## Option A: Microsoft Artifact Signing

Create an Artifact Signing account, complete identity validation, create a
public-trust certificate profile, and grant your signing identity the
`Artifact Signing Certificate Profile Signer` role. Install the official
client tools and Windows SDK SignTool:

```powershell
winget install -e --id Microsoft.Azure.ArtifactSigningClientTools
```

Create `metadata.json` outside the repository:

```json
{
  "Endpoint": "https://<region>.codesigning.azure.net",
  "CodeSigningAccountName": "<account-name>",
  "CertificateProfileName": "<profile-name>"
}
```

Then follow Microsoft's current SignTool command, substituting the installed
paths and the resolved EXE path:

```powershell
& "<Windows SDK>\x64\signtool.exe" sign /v /debug /fd SHA256 `
  /tr "http://timestamp.acs.microsoft.com" /td SHA256 `
  /dlib "<Artifact Signing Client>\x64\Azure.CodeSigning.Dlib.dll" `
  /dmdf "<private path>\metadata.json" `
  ".\dist\Jamfbreak.exe"
```

Official integration instructions:
[Artifact Signing with SignTool](https://learn.microsoft.com/azure/artifact-signing/how-to-signing-integrations).

## Option B: certificate in the Windows certificate store

Import the OV code-signing certificate into the current user's Personal
certificate store. Prefer a hardware-backed key and select it by thumbprint:

```powershell
signtool.exe sign /sha1 "<certificate-thumbprint>" /fd SHA256 `
  /tr "<your-CA-RFC3161-timestamp-URL>" /td SHA256 `
  /d "Jamfbreak" ".\dist\Jamfbreak.exe"
```

Do not put a PFX password in a script, workflow, repository secret printed to
logs, or command line. Never commit a `.pfx`, `.p12`, private key, or signing
token.

## Verification gate

Both commands must succeed before publication:

```powershell
signtool.exe verify /pa /all /v ".\dist\Jamfbreak.exe"
Get-AuthenticodeSignature ".\dist\Jamfbreak.exe" | Format-List Status,SignerCertificate,TimeStamperCertificate
Get-FileHash ".\dist\Jamfbreak.exe" -Algorithm SHA256
```

The Authenticode status must be `Valid`, the expected publisher must be shown,
and a timestamp certificate must be present.

If Microsoft Defender incorrectly detects the signed, reproducible release,
submit that exact file as a false positive through the
[Microsoft Security Intelligence portal](https://www.microsoft.com/wdsi/filesubmission).
Submit separate false-positive reports to any other vendor that detects it.
