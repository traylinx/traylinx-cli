# Security Policy

## Reporting Security Vulnerabilities

If you discover a security vulnerability in Traylinx CLI, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please email us at: **security@traylinx.com**

Include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (optional)

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 5 business days
- **Resolution**: Depends on severity, typically within 30 days

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | ✅ Yes             |
| < 0.2.0 | ❌ No              |

## Security Best Practices

When using Traylinx CLI:

1. **Never commit credentials** - Use environment variables or `~/.traylinx/config.yaml`
2. **Keep CLI updated** - Run `pip install --upgrade traylinx-cli` regularly
3. **Review agent manifests** - Check `traylinx-agent.yaml` before publishing

Thank you for helping keep Traylinx secure! 🔒
