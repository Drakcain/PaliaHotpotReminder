# Installer Signing

Current release: v3.1.5

PaliaHotpotReminder release installers are unsigned unless a release explicitly
states otherwise.

## Expected Windows Warnings

Unsigned installers may trigger Windows SmartScreen or browser download warnings.
This does not automatically mean the file is malicious, but it does mean Windows
has not established publisher reputation for that executable.

Expected installation flow:

```text
Download installer -> verify SHA-256 -> review SmartScreen if shown -> approve UAC -> setup completes
```

## Verify Releases

Use only release assets attached to this repository:

```text
https://github.com/Drakcain/PaliaHotpotReminder/releases
```

Each installer release should include a `.sha256` file. Confirm the downloaded
installer matches the published SHA-256 before running it.

## Future Signing

Do not claim code signing exists unless an actual Authenticode signing workflow
and certificate are in use.

Never commit certificate files, private keys, passwords, hardware-token
credentials, or signing service tokens. Any future GitHub Actions signing flow
must use protected repository or environment secrets.
