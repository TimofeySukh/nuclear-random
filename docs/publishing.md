# Publishing

The package name is `nuclear-random`.

Current release line:

```text
0.2.3: adds nuclear-prefixed helper names and keeps old aliases
0.2.2: longer default client and API wait windows for the slow physical pool
0.2.1: waits briefly for fresh entropy when the pool is empty
0.2.x: radioactive decay timing with Von Neumann debiasing
0.1.x: initial experimental hash-based extractor
```

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
