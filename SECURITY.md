# Security Policy

## Supported Versions

The following versions of Visionlog are currently receiving security updates:

| Version | Supported          |
| ------- | ------------------ |
| latest  | ✅ Yes             |
| older   | ❌ No              |

We strongly recommend keeping your installation up to date with the latest release.

## Reporting a Vulnerability

We take the security of Visionlog seriously. If you believe you have found a
security vulnerability, **please do not open a public GitHub issue**.

### How to Report

Send a detailed report to:

📧 **szmyty@gmail.com**

Please include the following information in your report:

* A clear description of the vulnerability
* Steps to reproduce the issue
* The potential impact (e.g., data exposure, denial of service)
* Any relevant logs, stack traces, or proof-of-concept code
* The version(s) of Visionlog affected

### What to Expect

* **Acknowledgement**: You will receive a confirmation within **48 hours**.
* **Assessment**: We will investigate the report and determine the severity and impact.
* **Resolution**: We aim to release a fix within **14 days** for critical issues, and
  **30 days** for lower-severity issues.
* **Disclosure**: Once a fix is available, we will coordinate with you on responsible
  public disclosure.

We appreciate your effort to responsibly disclose security issues and will credit
reporters in release notes unless anonymity is requested.

## Security Best Practices for Users

* **Privacy mode**: Visionlog's `privacy_mode` is enabled by default to prevent
  collection of PII (IP addresses, geo-location, device data). Only disable it
  if you have a lawful basis and have met your compliance obligations.
* **Keep dependencies updated**: Regularly update Visionlog and its dependencies
  to pick up security patches.
* **Limit log exposure**: Ensure log output is sent only to trusted destinations
  and is not inadvertently exposed in public channels.
