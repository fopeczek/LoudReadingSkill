# Installation

## Dependencies

This package requires `pyaudio` to capture sound from the microphone. `pyaudio` requires `portaudio19-dev` package to be installed on the system. On Ubuntu, this package can be installed via `apt` package manager.
```bash
sudo apt install portaudio19-dev
```

## Main application

The recommended way to install this package is via `pipx`. `Pipx` is a tool to install Python packages globally in their own environment. Pipx can be installed on Ubuntu via `apt` package manager.
```bash
sudo apt install pipx
```

Once `pipx` is installed, you can install this package via the following command:
```bash
pipx install git+https://github.com/fopeczek/LoudReadingSkill --python $(which python3.12)
```

The `--python` flag is used to specify the Python version to use. This package requires Python 3.12 or newer. If your system already has Python 3.12 installed, you can omit the `--python` flag.
