# Publishing

The package name is `nuclear-random`.

## Build Locally

```bash
python -m pip install --upgrade build
python -m build
```

## Test Before Release

```bash
python -m pytest
ruff check .
arduino-cli compile --fqbn esp32:esp32:esp32c3:CDCOnBoot=cdc firmware/esp32c3_geiger_entropy
```

## PyPI

The repository includes a GitHub Actions publish workflow for PyPI trusted publishing. Configure the PyPI project to trust:

```text
Owner: TimofeySukh
Repository: nuclear-random
Workflow: publish.yml
Environment: pypi
```

Publish by creating a GitHub release from a version tag.

