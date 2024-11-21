# catgit

**_`catgit` is a Python-based cli tool to dump out an entire directory structure or a git project in a `cat`-esque way or to pass it along into a text editor into a single file_**

`catgit` is intended to display the contents of a Git project in a consolidated, readable format directly in your terminal or through a specified text editor. It provides a quick overview of the project's structure, including ignored files based on your `.gitignore` settings, and can output all readable files sequentially.

`catgit` supports direct dumps of an entire project's contents straight into your favorite text editor, i.e. to be passed along to a LLM assistant or such with the `--editor` flag. It can also be used to get the structural view of regular directories and their file contents, even if they're not Git repositories.

`catgit` has its own `.catgitignore` ignore lists and `.catgitinclude` include lists, both work the same way as `.gitignore` does. You can use `.catgitignore` to ignore files that you don't want to be included in your project directory tree dump, or `.catgitinclude` (with the `--includedonly` command line flag) to only include the files listed in the include file.

## Features

- **`.catgitignore`**: (New) Read and respect `.catgitignore` files to skip over additional files or directories specific to `catgit` outputs.
    - Further reduces extra context clutter during printouts. 
    - Can be used the same way as `.gitignore` files.
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
- `treat_non_git_as_error`: Decide whether to quit if the directory structure is not recognized as a Git repository.
- `.catgitinclude` and `.catgitignore` files to ignore files or only list included (works akin to `.gitignore`)

Please see the `config.ini` for more configuration options.

## Usage

To use `catgit`, navigate to the root directory of the project and run:
```bash
catgit /path/to/your/project/
```

You can also pass the output directly to your editor with the flag `--editor` (since v`0.10.4`):
```bash
catgit /path/to/your/project/ --editor
```

Or, `cd` to your project directory and simply run:
```bash
catgit . --editor
```

You will be prompted for an editor if a default isn't found. You can use i.e. `vim`, `nano` etc on Linux, `notepad` on Windows, etc.

## Help

After having been installed, help for using `catgit` is available by typing:

```bash
catgit --help
```

## Changes
- `0.11.2` - added the `.catgitinclude` feature
    - this allows to only print out selected files from the project, as listed in the include file
    - the logic is similar to `.gitignore` (or `.catgitignore`), except it's files to _include_, not to _exclude_
    - can be utilized with `--includeonly` cmdline flag
- `0.11.1` - subprocess optimization (speeds up `catgit` on larger projects)
- `0.11.0` - added `.catgitignore` functionality to ignore files
    - works the same way as `.gitignore`, is useful for selective project outputs
    - also added `debug_mode` (true/false) flag into `config.ini` for verbose mode
- `0.10.8` - output clarification to minimize LLM confusion and `--version`
- `0.10.7` - added `ThreadPoolExecutor` for faster performance; file sizes; line counting
- `0.10.6` - added the `treat_non_git_as_error` (true/false) config option
- `0.10.5` - git checks made robust and verbose
- `0.10.4` - added `--editor` flag for sending straight to text editor, checks for editor and asks the user if not found
- `0.10.3` - improved error catching, absolute paths
- `0.10.2` - switched to using `tempfile` for better cross-platform compatibility
- `0.10.1` - added the `--setup` flag for quick setup in cli
- `0.10` - initial public release w/ installer

## Credits

`catgit` was developed by [FlyingFathead](https://github.com/FlyingFathead) with digital ghost code contributions from ChaosWhisperer. 

## About `catgit`

This tool is designed to streamline the process of reviewing project contents, making it a neat little utility for developers who manage large or complex Git repositories and/or use LLM-based AI assistants to sort through their codebases.

## License

`catgit` is open-source software licensed under the MIT license.
