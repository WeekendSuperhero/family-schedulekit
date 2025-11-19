# Contributing to family-schedulekit

Thanks for your interest in contributing! This document provides guidelines and information for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Reporting Issues](#reporting-issues)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Running Tests](#running-tests)
- [Code Style](#code-style)
- [Pull Request Process](#pull-request-process)
- [License](#license)

## Code of Conduct

This project follows a code of conduct based on respect and professionalism:

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment for all contributors
- Report unacceptable behavior to weekend@weekendsuperhero.io

## Getting Started

Before contributing:

1. Check existing [issues](https://github.com/weekendsuperhero/family-schedulekit/issues) and [pull requests](https://github.com/weekendsuperhero/family-schedulekit/pulls)
2. For major changes, open an issue first to discuss your ideas
3. Fork the repository and create a feature branch

## Reporting Issues

When reporting bugs or requesting features, please include:

- **For bugs:**
  - Python version and OS
  - Steps to reproduce the issue
  - Expected vs. actual behavior
  - Error messages or logs
  - Minimal example that reproduces the problem

- **For feature requests:**
  - Clear description of the feature
  - Use cases and benefits
  - Any relevant examples or mockups

Use the [issue templates](.github/ISSUE_TEMPLATE/) when available.

## Development Setup

1. **Fork and clone the repository:**

```bash
git clone https://github.com/YOUR-USERNAME/family-schedulekit.git
cd family-schedulekit
```

2. **Install dependencies with uv:**

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable package management.

**Install uv** (if you don't have it):

```bash
# Bash/Zsh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

```fish
# Fish
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Sync dependencies:**

```bash
# All shells
uv sync --extra dev
```

3. **Verify installation:**

```bash
# Run tests
uv run pytest

# Check code style
uv run ruff check .

# Run type checker
uv run mypy src/family_schedulekit
```

## Making Changes

1. **Create a feature branch:**

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

2. **Make your changes:**
   - Write clear, documented code
   - Add tests for new functionality
   - Update documentation as needed
   - Follow the existing code style

3. **Commit your changes:**

```bash
git add .
git commit -m "Add clear commit message describing changes"
```

Use clear, descriptive commit messages:

- `feat: Add support for timezone-aware schedules`
- `fix: Resolve modulo calculation error for week 53`
- `docs: Update installation instructions`
- `test: Add tests for swap color shading`

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=family_schedulekit

# Run specific test file
uv run pytest tests/test_resolver_pytest.py

# Run tests matching a pattern
uv run pytest -k "test_modulo"
```

## Code Style

This project uses:

- **[Ruff](https://docs.astral.sh/ruff/)** for linting and formatting
- **[mypy](https://mypy.readthedocs.io/)** for type checking
- **Type hints** throughout the codebase

### Running style checks:

```bash
# Check code style
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .

# Format code
uv run ruff format .

# Type checking
uv run mypy src/family_schedulekit
```

### Style guidelines:

- Maximum line length: 160 characters
- Use type hints for all function parameters and return values
- Write docstrings for public functions and classes
- Follow PEP 8 conventions (enforced by Ruff)
- Prefer explicit over implicit
- Keep functions focused and single-purpose

## Pull Request Process

1. **Update your branch:**

```bash
git fetch upstream
git rebase upstream/main
```

2. **Ensure all checks pass:**
   - All tests pass
   - Code style checks pass
   - Type checking passes
   - No new warnings

3. **Update documentation:**
   - Update README.md if needed
   - Add entries to CHANGELOG.md
   - Update docstrings

4. **Submit pull request:**
   - Use a clear, descriptive title
   - Reference any related issues
   - Describe what changed and why
   - Include screenshots for visual changes
   - List any breaking changes

5. **Review process:**
   - Maintainers will review your PR
   - Address any feedback or requested changes
   - Once approved, your PR will be merged

## Project Structure

```
family-schedulekit/
├── src/family_schedulekit/    # Main package code
│   ├── __init__.py           # Package initialization
│   ├── cli.py                # CLI commands
│   ├── models.py             # Pydantic models
│   ├── resolver.py           # Schedule resolution logic
│   ├── visualizer.py         # PNG generation
│   ├── exporter.py           # Export functionality
│   ├── colors.py             # Color utilities
│   ├── config.py             # Configuration handling
│   ├── resources.py          # Template resources
│   └── ai_helper.py          # AI context generation
├── tests/                    # Test files
├── schema/                   # JSON schema definitions
├── examples/                 # Example configs and outputs
├── README.md                 # Main documentation
├── CONTRIBUTING.md           # This file
├── CHANGELOG.md              # Version history
└── pyproject.toml            # Project configuration
```

## Adding New Features

When adding features:

1. **Design first:**
   - Consider backward compatibility
   - Think about the user experience (CLI and API)
   - Ensure the schema remains machine-readable

2. **Implementation:**
   - Add models to `models.py` if needed
   - Implement logic in appropriate modules
   - Add CLI commands to `cli.py` if relevant
   - Update the JSON schema in `schema/`

3. **Testing:**
   - Add unit tests for new functionality
   - Test edge cases
   - Ensure existing tests still pass

4. **Documentation:**
   - Update README with examples
   - Add docstrings
   - Update CHANGELOG.md

## License

By contributing to family-schedulekit, you agree that your contributions will be licensed under the project's dual license:

- **PolyForm Noncommercial 1.0.0** for non-commercial use
- **Commercial License** for commercial use

See [LICENSE](LICENSE), [LICENSE-NONCOMMERCIAL](LICENSE-NONCOMMERCIAL), and [LICENSE-COMMERCIAL](LICENSE-COMMERCIAL) for details.

All contributions must be original work or properly attributed if using external code/resources.

## Development Environment

This project is primarily developed on:

- **macOS** with **Fish shell**
- **Python 3.14** with modern language features
- **uv** for package management

While the package is OS-independent and works with all shells, documentation examples include Bash, Zsh, and Fish syntax for inclusivity.

## Questions?

- Open an [issue](https://github.com/weekendsuperhero/family-schedulekit/issues)
- Email: weekend@weekendsuperhero.io
- Check existing documentation in the [README](README.md)

Thank you for contributing to family-schedulekit! 🎉
