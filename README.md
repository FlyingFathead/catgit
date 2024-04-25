# catgit

_A Python cli tool to dump out a git project in a `cat`-esque way_

`catgit` is a Python CLI tool designed to display the contents of a Git project in a consolidated, readable format directly in your terminal or through a specified text editor. It provides a quick overview of the project's structure, including ignored files based on your `.gitignore` settings, and can output all readable files sequentially.

## Features

- **Project Overview**: Outputs the complete directory and file structure of your Git project.
- **Gitignore Respect**: Respects `.gitignore` files to skip over ignored files or directories.
- **Flexible Output**: Supports output directly to the terminal or opens in a specified text editor like nano or gedit.
- **Configurable**: Options to toggle the inclusion of the tree view in the output, and choose between terminal output and editor output through configuration.

## Configuration

`catgit` uses a configuration file (`config.ini`) which allows the user to set preferences such as:

- `output_method`: Choose between `terminal` and `editor` to display the project output.
- `editor_command`: Specify which editor to use when opening the output (e.g., `nano`, `gedit`).
- `ignore_gitignored`: Toggle whether to ignore files as specified in `.gitignore`.
- `include_tree_view_in_file`: Decide whether to include the directory tree structure in the concatenated file output.

Example configuration (`config.ini`):

```ini
[Defaults]
output_method = editor
editor_command = nano
ignore_gitignored = true
include_tree_view_in_file = true```

## Usage

To use catgit, navigate to the root directory of the project and run:

```bash
python catgit.py /path/to/your/project/```

## Credits

catgit was developed by FlyingFathead with contributions from ChaosWhisperer. This tool is designed to streamline the process of reviewing project contents, making it an invaluable utility for developers who manage large or complex Git repositories and/or use LLM-based AI assistants to sort through their codebases.

## License

catgit is open-source software licensed under the MIT license.
