set fallback

# Installs remote dependencies.
dep:
  #!/usr/bin/env bash
  set -euo pipefail
  # Check if nvidia is available:
  if lspci | grep -i '.* vga .* nvidia .*' &> /dev/null; then
    echo "Nvidia GPU detected. Proceeding with local dependencies."
    just dep-local
  else
    echo "Nvidia GPU not detected. Installing remote dependencies."
    just dep-remote
  fi

# Installs remote dependencies.
dep-remote:
  #!/usr/bin/env bash
  set -euo pipefail
  poetry install

# Installs local dependencies. Requires nvidia.
dep-local:
  #!/usr/bin/env bash
  set -euo pipefail
  # Check if nvidia is available:
  if ! lspci | grep -i '.* vga .* nvidia .*' &> /dev/null; then
    echo "Nvidia GPU not detected. Please install the local dependencies manually."
    exit 1
  fi
  poetry install --extras local

# installs pre-commit hooks (and pre-commit if it is not installed)
install-hooks: install-pre-commit
  #!/usr/bin/env bash
  set -euo pipefail
  if [ ! -f .git/hooks/pre-commit ]; then
    pre-commit install
  fi

[private]
install-pre-commit:
  #!/usr/bin/env bash
  set -euo pipefail
  # Check if command pre-commit is available. If yes - exists
  if command -v pre-commit &> /dev/null; then
    exit 0
  fi
  # Check if pipx exists. If it does not, asks
  if ! command -v pipx &> /dev/null; then
    echo "pipx is not installed. It is recommended to install pre-commit using pipx rather than pip. Please install pipx using `pip install pipx` and try again."
    exit 1
  fi
  pipx install pre-commit

# Downloads remote dependencies and installs the git commit hooks
setup-dev-remote: dep install-hooks

# Downloads LOCAL dependencies and installs the git commit hooks. Requires nvidia.
setup-dev-local: dep-local install-hooks

# Runs the pre-commit checks. "all" runs checks on all files, not only the dirty ones.
check arg="dirty": install-pre-commit
  #!/usr/bin/env bash
  set -euo pipefail
  if [[ "{{arg}}" == "all" ]]; then
    pre-commit run --all-files
  else
    pre-commit run
  fi
