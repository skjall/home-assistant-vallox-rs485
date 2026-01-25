---
name: Bug Report
about: Report a bug to help improve the integration
title: '[Bug] '
labels: bug
assignees: ''
---

## Description

A clear and concise description of what the bug is.

## Environment

- **Home Assistant Version**:
- **Integration Version**:
- **Vallox Model**: (e.g., Vallox 90 SE, Digit SE)
- **RS485 Adapter**: (e.g., Waveshare USB-RS485)
- **Installation Method**: HACS / Manual

## Steps to Reproduce

1. Go to '...'
2. Click on '...'
3. See error

## Expected Behavior

What you expected to happen.

## Actual Behavior

What actually happened.

## Logs

<details>
<summary>Home Assistant Logs</summary>

```
Paste relevant logs here (Settings → System → Logs)
Enable debug logging first if needed:
logger:
  logs:
    custom_components.vallox_rs485: debug
```

</details>

## Hardware Setup

- [ ] Wiring verified (A→A, B→B, GND→M)
- [ ] Not connected to 24V power pins
- [ ] Adapter recognized by system (`ls /dev/tty*`)

## Additional Context

Add any other context, screenshots, or information here.

## Checklist

- [ ] I have searched existing issues for duplicates
- [ ] I am using the latest version of the integration
- [ ] I have included relevant logs
- [ ] I have verified my hardware setup
