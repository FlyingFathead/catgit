# catgit

_A Python cli tool to dump out a git project in a `cat`-esque way or to pass it along into a text editor in one file_

`catgit` is a Python CLI tool designed to display the contents of a Git project in a consolidated, readable format directly in your terminal or through a specified text editor. It provides a quick overview of the project's structure, including ignored files based on your `.gitignore` settings, and can output all readable files sequentially. 

It also supports directly dumping out the entire project straight into your favorite text editor to be i.e. passed along to a LLM assistant or such.

## Features

- **Project Overview**: Outputs the complete directory and file structure of your Git project.
- **Gitignore Respect**: Respects `.gitignore` files to skip over ignored files or directories.
- **Flexible Output**: Supports output directly to the terminal or opens in a specified text editor like nano or gedit.
- **Configurable**: Options to toggle the inclusion of the tree view in the output, and choose between terminal output and editor output through configuration.

## Installation

You can install `catgit` directly from the source code:

1. Clone the repository:
```bash
git clone https://github.com/FlyingFathead/catgit.git
```
2. Navigate to the cloned directory:
```bash
cd catgit
```
3. Install the package:
```bash
pip install .
```

### Using without install

Alternatively, if you only want to try out `catgit`, navigate to the `catgit/` subdirectory and run it with:
```bash
python catgit.py /path/to/your/project/
```

## Configuration

For quick setup after installation, just use:
```bash
catgit --setup
```

`catgit` uses a configuration file (`config.ini`) which allows the user to set preferences such as:

- `output_method`: Choose between `terminal` and `editor` to display the project output.
- `editor_command`: Specify which editor to use when opening the output (e.g., `vim`, `nano`, `gedit`).
- `ignore_gitignored`: Toggle whether to ignore files as specified in `.gitignore`.
- `include_tree_view_in_file`: Decide whether to include the directory tree structure in the concatenated file output.

Example configuration (`config.ini`):

```ini
[Defaults]
output_method = editor
editor_command = vim
ignore_gitignored = true
include_tree_view_in_file = true
```

## Usage

To use catgit, navigate to the root directory of the project and run:
```bash
catgit /path/to/your/project/
```

You can also pass the output directly to your editor with the flag `--editor` (since v`0.10.4`):
```bash
catgit /path/to/your/project/ --editor
```

You will be prompted for an editor if a default isn't found. You can use i.e. `vim`, `nano` etc on Linux, `notepad` on Windows.

## Changes
- `0.10.5` - git checks more robust and verbose now
- `0.10.4` - added `--editor` flag for sending straight to text editor, checks for editor and asks the user if not found
- `0.10.3` - improved error catching, absolute paths
- `0.10.2` - switched to using `tempfile` for better cross-platform compatibility
- `0.10.1` - added the `--setup` flag for quick setup in cli
- `0.10` - initial public release w/ installer

## Credits

`catgit` was developed by FlyingFathead with contributions from ChaosWhisperer. 

## About `catgit`

This tool is designed to streamline the process of reviewing project contents, making it a neat little utility for developers who manage large or complex Git repositories and/or use LLM-based AI assistants to sort through their codebases.

## License

`catgit` is open-source software licensed under the MIT license.
