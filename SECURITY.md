# Security policy

## Reporting a vulnerability

Please do not report security problems in public issues. Use GitHub's private vulnerability reporting (**Security → Report a vulnerability** on this repository) or contact the maintainer privately through the GitHub profile [@artepe](https://github.com/artepe). Please allow time for a fix before publishing details.

## Supported versions

Security fixes are made to the latest release and the `main` branch only.

## Security design

- The Home Assistant token is read from the `HA_TOKEN` environment variable only. It is never written to snapshots or reports, and redirects are refused so the bearer token is never forwarded to another host.
- HTML reports escape every value and load no external scripts or styles.
