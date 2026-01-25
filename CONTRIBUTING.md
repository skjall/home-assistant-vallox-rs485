# Contributing to Vallox RS485

Thank you for your interest in contributing to the Vallox RS485 integration for Home Assistant.

## Getting Started

### Prerequisites

- Python 3.11+
- Home Assistant development environment
- USB-RS485 adapter (for hardware testing)
- Basic understanding of the RS485 protocol

### Development Setup

1. Fork and clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   ```
3. Install development dependencies:
   ```bash
   pip install -r requirements_dev.txt
   ```
4. Link to your Home Assistant config:
   ```bash
   ln -s $(pwd)/custom_components/vallox_rs485 ~/.homeassistant/custom_components/vallox_rs485
   ```

### Testing without Hardware

Use virtual serial ports for development:
```bash
socat -d -d pty,raw,echo=0 pty,raw,echo=0
```

## How to Contribute

### Reporting Bugs

- Use the [Bug Report](../../issues/new?template=bug_report.md) template
- Include Home Assistant and integration version
- Attach relevant logs (Settings → System → Logs)
- Describe your hardware setup (adapter model, wiring)

### Suggesting Features

- Use the [Feature Request](../../issues/new?template=feature_request.md) template
- Check existing issues to avoid duplicates
- Describe the use case and expected behavior

### Pull Requests

1. Create a feature branch from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. Make your changes following the code style guidelines
3. Test your changes thoroughly
4. Update documentation if needed
5. Submit a pull request to the `development` branch

## Code Style Guidelines

### Python

- Follow PEP 8
- Use type hints for function parameters and return values
- Keep functions focused and under 50 lines
- Use descriptive variable names

### Commits

- Use conventional commit messages:
  - `feat:` New features
  - `fix:` Bug fixes
  - `docs:` Documentation changes
  - `refactor:` Code refactoring
  - `test:` Test additions/changes
  - `chore:` Maintenance tasks

Example:
```
feat: add CO2 sensor support

- Add CO2 register reading
- Convert raw value to ppm
- Create sensor entity
```

### Documentation

- Write in English
- Update README.md for user-facing changes
- Update CLAUDE.md for architectural changes
- Add inline comments for complex protocol logic

## Translations

We welcome translations. To add a new language:

1. Copy `translations/en.json` to `translations/{lang_code}.json`
2. Translate all strings
3. Test in Home Assistant with that language setting
4. Submit a pull request

Current languages: en, de, fr, es, it, nl, pl, pt, sv, nb, da, fi, cs, uk, zh-Hans

## Protocol Documentation

When working on protocol-related changes:

- Reference the [FHEM Vallox Wiki](https://wiki.fhem.de/wiki/Vallox)
- Document any new registers in `const.py`
- Update the protocol reference in CLAUDE.md
- Test with real hardware if possible

## Questions?

- Open a [Discussion](../../discussions) for general questions
- Check existing issues and discussions first
- Be patient and respectful

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
