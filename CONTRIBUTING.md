# Contributing

Thank you for contributing to Telegram MCP Next Generation.

## Development setup

Use Python 3.11 or 3.12. Create an isolated environment, install the development dependencies, and run the offline test suite before opening a change:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
pytest -q
```

## Change requirements

Keep pull requests focused and preserve the public MCP tool names, parameters, annotations, compatibility entrypoints, and safe configuration defaults. Do not include Telegram credentials, session files, runtime databases, personal chat data, generated build output, or local logs. New behavior should include deterministic tests and documentation where appropriate.

For changes to authentication, mutation gates, filesystem handling, media paths, retry policy, concurrency, or SQLite persistence, include failure-path coverage and state whether live Telegram behavior was tested. Live account operations must not be used in automated tests.

Before submitting a pull request, run the repository test suite, focused coverage gate, syntax lint, typed shared-layer checks, package build, and dependency audit. Docker validation should be run on a Docker-capable environment when container files change.

## Pull requests

Explain the problem, summarize the implementation, identify compatibility implications, and list the verification commands and outcomes. Keep unrelated formatting or dependency upgrades out of the change. Maintainers may request a smaller patch when a safer shared-layer fix is available.

## License

By contributing, you agree that your contribution is provided under the Apache License 2.0. Project maintenance is provided by LoneVertex.
