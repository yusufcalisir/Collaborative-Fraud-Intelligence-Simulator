# Contributing

Contributions are welcome. This section outlines how to get started.

## Development Setup

1. Clone the repo
2. Copy `.env.example` to `.env`
3. Start services: `make dev`
4. Backend runs at `http://localhost:8000`, frontend at `http://localhost:3000`

## Code Standards

- **Python**: Follows ruff linting rules. Run `make lint` before committing.
- **TypeScript**: Strict mode enabled. Run `npx tsc --noEmit` to type-check.
- **Commits**: Use conventional commit messages (`feat:`, `fix:`, `docs:`, `refactor:`).

## Running Tests

```bash
make test          # All backend tests
make test-unit     # Unit tests only
make lint          # Lint check
```

## Pull Request Process

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Ensure tests pass and linting is clean
5. Submit a PR with a clear description

## Architecture

Read `docs/architecture.md` before making structural changes. The project follows Clean Architecture with four layers:

- **Domain** — Business entities and value objects
- **Application** — Services, schemas, interface contracts
- **Infrastructure** — Database, cache, task queue
- **Presentation** — API routers, WebSocket handlers

Dependencies flow inward: Presentation → Application → Domain. Infrastructure implements Application interfaces.
