# Contributing to Traylinx CLI

Thank you for your interest in contributing to Traylinx CLI! 🎉

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/traylinx-cli.git
   cd traylinx-cli
   ```
3. **Install development dependencies**:
   ```bash
   uv sync
   ```

## Development Workflow

### Running Locally

```bash
# Run CLI in development mode
uv run traylinx --help

# Or use the short alias
uv run tx --help
```

### Running Tests

```bash
uv run pytest
```

### Code Style

We use [Ruff](https://github.com/astral-sh/ruff) for linting:

```bash
uv run ruff check .
uv run ruff format .
```

## Making Changes

1. **Create a branch** for your feature or fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and commit with clear messages:
   ```bash
   git commit -m "feat: add new command for X"
   ```

3. **Push your branch** and create a Pull Request

## Commit Message Format

We follow [Conventional Commits](https://conventionalcommits.org/):

- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `chore:` - Maintenance tasks
- `refactor:` - Code refactoring

## Pull Request Guidelines

- Keep PRs focused on a single change
- Update documentation if needed
- Add tests for new functionality
- Ensure all tests pass before submitting

## Reporting Issues

- Use GitHub Issues to report bugs
- Include CLI version (`traylinx --version`)
- Include Python version and OS
- Provide steps to reproduce

## Code of Conduct

Be respectful and inclusive. We welcome contributors of all backgrounds.

## Questions?

Open an issue or reach out at [dev@traylinx.com](mailto:dev@traylinx.com).

---

Thank you for contributing! 🚀
