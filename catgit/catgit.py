# catgit.py
# https://github.com/FlyingFathead/catgit
# 2024 -/- FlyingFathead (w/ ChaosWhisperer)

version_number = "0.11.4"

import sys
import tempfile
import argparse
import subprocess
import os
import configparser
import logging
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import fnmatch
import re

# Initial placeholder for logging configuration
# It will be set after loading the config
logger = logging.getLogger(__name__)

def check_editor_availability(editor):
    """Check if the editor is available in the system's PATH."""
    return shutil.which(editor) is not None

def get_valid_editor(current_editor):
    """Prompt the user for a valid editor if the current one is not found."""
    while True:
        editor = input(f"The editor '{current_editor}' is not found. Please enter a valid editor command or press Enter to cancel: ").strip()
        if not editor:  # User cancels the input
            print("Editor update canceled.")
            return None
        if check_editor_availability(editor):
            return editor
        print(f"The editor '{editor}' is not available.")

def update_config(config_path, section, option, value):
    """Update the specified configuration option with a new value."""
    config = configparser.ConfigParser()
    config.read(config_path)
    config.set(section, option, value)
    with open(config_path, 'w') as configfile:
        config.write(configfile)
    print(f"Configuration updated: {option} set to {value}")

def load_config():
    # Config paths
    script_dir = Path(__file__).resolve().parent
    local_config_path = script_dir / 'config.ini'
    global_config_path = Path.home() / '.config' / 'catgit' / 'config.ini'

    config = configparser.ConfigParser()
    config.read_dict({'Defaults': {
        'output_method': 'terminal',  # Default to terminal
        'editor_command': 'nano',  # Default to nano for editing
        'include_tree_view_in_file': 'true',  # Default to including tree view in the file output
        'treat_non_git_as_error': 'false',  # Default to not treating non-git directories as error
        'catgitignore_enabled': 'true',  # Default to enabled
        'catgitignore_file': '.catgitignore',  # Default .catgitignore file name
        'markup_catgitignored_files': 'true',  # Default to marking up ignored files
        'display_catgitignored_files': 'true',   # Default to displaying ignored files
        'always_exclude_dirs': '.git,__pycache__,.venv,env,venv,build,dist,catgit.egg-info',  # Default excluded dirs
        'debug_mode': 'false',  # Default to false
        'catgitinclude_enabled': 'true',  # Default to enabled
        'catgitinclude_file': '.catgitinclude',  # Default .catgitinclude file name
        'hide_nonexistent_gitignored': 'false',  # Whether to skip non-existent ignored files        
        'use_extra_delimiter': 'true',  # Default to using an extra per-file delimiter
        'extra_delimiter_type': '~~~'  # Default to tildes for extra delimiter
    }})

    # Read configuration from paths
    read_files = config.read([str(local_config_path), str(global_config_path)])
    if not read_files:
        print("No config file found, using default settings.")

    return config, local_config_path if local_config_path.exists() else global_config_path

def save_config(config, path):
    with open(path, 'w') as configfile:
        config.write(configfile)
    print(f"Configuration saved to: {path}")

def setup_config():
    config, config_path = load_config()
    print(f"::: catgit v{version_number} -- current settings:")
    for section in config.sections():
        for key, value in config.items(section):
            print(f"{key}: {value}")

    print("\nModifying settings (press ENTER to keep current value)...\n")
    for section in config.sections():
        for key in config[section]:
            current_value = config[section][key]
            new_value = input(f"Enter new value for {key} ({current_value}): ").strip()
            config[section][key] = new_value if new_value else current_value  # Only update if a new value is entered

    save_config(config, config_path) 

def is_git_repository(path):
    try:
        result = subprocess.run(['git', '-C', path, 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True
        else:
            logger.error(f"Git check failed with message: {result.stderr.strip()}")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command exception: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking Git repository: {e}")
        return False

def get_git_remote_url(path):
    try:
        result = subprocess.run(
            ['git', '-C', path, 'config', '--get', 'remote.origin.url'],
            capture_output=True, text=True, check=True
        )
        if result.stdout.strip():
            return result.stdout.strip()
        else:
            logger.info(f"No remote URL set for the repository at {path}.")
            return "No remote URL set."
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed with error: {e.stderr}")
        return "No remote URL found."
    except Exception as e:
        logger.error(f"Unexpected error when trying to get git remote URL: {e}")
        return "No remote URL found."

def parse_catgitignore(catgitignore_path):
    """Parse the .catgitignore file and return a list of compiled regex patterns."""
    patterns = []
    try:
        with open(catgitignore_path, 'r') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Convert glob patterns to regex
                    regex = fnmatch.translate(line)
                    try:
                        patterns.append(re.compile(regex))
                    except re.error as e:
                        logger.error(f"Invalid pattern in .catgitignore at line {line_number}: '{line}'. Error: {e}")
    except FileNotFoundError:
        logger.info(f"No `.catgitignore` file at: {catgitignore_path}")
    except Exception as e:
        logger.error(f"Error reading {catgitignore_path}: {e}")
    logger.debug(f"Parsed .catgitignore with {len(patterns)} compiled patterns.")
    return patterns

def parse_catgitinclude(catgitinclude_path):
    """Parse the .catgitinclude file and return a list of compiled regex patterns."""
    patterns = []
    try:
        with open(catgitinclude_path, 'r') as f:
            for line_number, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Convert glob patterns to regex
                    regex = fnmatch.translate(line)
                    try:
                        patterns.append(re.compile(regex))
                    except re.error as e:
                        logger.error(f"Invalid pattern in .catgitinclude at line {line_number}: '{line}'. Error: {e}")
    except FileNotFoundError:
        logger.error(f"No `.catgitinclude` file at: {catgitinclude_path}")
    except Exception as e:
        logger.error(f"Error reading {catgitinclude_path}: {e}")
    logger.debug(f"Parsed .catgitinclude with {len(patterns)} compiled patterns.")
    return patterns

def get_all_files(path):
    """Generator to yield all file paths relative to the root path."""
    for root, dirs, files in os.walk(path):
        for file in files:
            yield os.path.relpath(os.path.join(root, file), start=path)

def get_all_git_ignored_files(path):
    """Retrieve all Git-ignored files and directories in the repository."""
    ignored_files = set()
    try:
        # Use git ls-files to list all ignored files and directories
        git_cmd = ['git', '-C', path, 'ls-files', '--others', '--ignored', '--exclude-standard', '--directory']
        result = subprocess.run(git_cmd, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            # Convert to a set of normalized relative paths
            ignored_files = set(os.path.normpath(file) for file in result.stdout.strip().split('\n'))
        logger.debug(f"Retrieved {len(ignored_files)} Git-ignored files and directories: {ignored_files}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e.stderr}")
    except Exception as e:
        logger.error(f"Unexpected error while retrieving Git-ignored files: {e}")
    return ignored_files

def get_included_files_and_dirs(path, compiled_include_patterns):
    """Retrieve all files and directories that match the include patterns."""
    included_files = set()
    included_dirs = set()

    for root, dirs, files in os.walk(path):
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, start=path)
            for pattern in compiled_include_patterns:
                if pattern.match(relative_path):
                    included_files.add(relative_path)
                    # Add all parent directories to included_dirs
                    dir_path = os.path.dirname(relative_path)
                    while dir_path:
                        included_dirs.add(dir_path)
                        dir_path = os.path.dirname(dir_path)
                    included_dirs.add('.')  # Include root directory
                    break  # No need to check other patterns

    logger.debug(f"Found {len(included_files)} included files and {len(included_dirs)} included directories.")
    return included_files, included_dirs

def is_catgit_ignored(relative_path, compiled_patterns):
    """Determine if a file or directory should be ignored based on compiled .catgitignore patterns."""
    # Normalize the path to always include a trailing slash for directories
    normalized_path = relative_path + '/' if os.path.isdir(relative_path) else relative_path

    for pattern in compiled_patterns:
        if pattern.match(normalized_path):
            logger.debug(f"Ignoring {relative_path} due to .catgitignore pattern: {pattern.pattern}")
            return True
    return False

def is_text_file(file_path):
    """Determine if a file is a text file based on its content."""
    try:
        with open(file_path, 'rb') as f:
            content = f.read(1024)  # Read the first 1024 bytes
        if content:
            text_chars = {7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x7f))
            nontext_char_count = sum(1 for byte in content if byte not in text_chars)
            percentage_of_text_chars = 100 * (1 - nontext_char_count / len(content))
            return percentage_of_text_chars > 70
        else:
            return True  # Empty files are considered text files
    except ZeroDivisionError:
        logger.error(f"Zero division error when processing the file, skipping: {file_path}")
        return False  # Handle the division by zero explicitly
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        return False

def process_file(full_path, extra_delimiter):
    """Process individual file to get content and metadata."""
    try:
        with open(full_path, 'r', errors='ignore') as file:
            content = file.read()
        file_size = os.stat(full_path).st_size
        num_lines = content.count('\n')
        
        # Extract file extension for syntax highlighting
        _, ext = os.path.splitext(full_path)
        ext = ext.lstrip('.').lower()  # Remove the dot and convert to lowercase

        # Map common extensions to language identifiers
        language_mapping = {
            'md': 'markdown',
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'rb': 'ruby',
            'go': 'go',
            'rs': 'rust',
            'php': 'php',
            'kt': 'kotlin',
            'swift': 'swift',
            'scala': 'scala',
            'lua': 'lua',
            'sql': 'sql',
            'yml': 'yaml',
            'yaml': 'yaml',
            'ini': 'ini',
            # Add more extensions as needed
        }

        language = language_mapping.get(ext, '')  # Default to empty string if unknown

        # Check if delimiter is enabled
        if extra_delimiter:
            # Use the delimiter from configuration
            content_block = f"{extra_delimiter}{language}\n{content}\n{extra_delimiter}"
        else:
            content_block = content

        return f"\n==== [ {full_path} | Size: {file_size} bytes | Lines: {num_lines} ] ====\n{content_block}\n"
    except Exception as e:
        return f"\n==== [ {full_path} ] ==== SKIPPED (Error: {str(e)})\n"

def concatenate_and_generate_tree(path, ignored_git_files, compiled_catgit_patterns, include_tree_view,
                                  markup_catgitignored_files, display_catgitignored_files, always_exclude_dirs,
                                  ignore_gitignored, display_gitignored_files,
                                  include_only=False, included_files=None, included_dirs=None,
                                  hide_nonexistent_gitignored=False, extra_delimiter=''):

    """Traverse the directory once to generate tree view and concatenate file contents."""
    tree_output = ""
    concatenated_output = []
    futures = []
    files_to_skip = {'.gitignore', '.catgitignore', '.catgitinclude'}

    def traverse(current_path, prefix='', relative_path=''):
        nonlocal tree_output, concatenated_output

        # Enforce strict inclusion for directories
        if include_only and relative_path and relative_path not in included_dirs:
            return

        try:
            entries = sorted(os.listdir(current_path))
        except OSError as e:
            logger.error(f"Error listing directory {current_path}: {e}")
            return

        # Exclude unwanted directories
        entries = [
            e for e in entries
            if not (os.path.isdir(os.path.join(current_path, e)) and e in always_exclude_dirs)
        ]

        total_entries = len(entries)

        for index, entry in enumerate(entries):
            full_path = os.path.join(current_path, entry)
            entry_relative_path = os.path.join(relative_path, entry) if relative_path else entry
            entry_relative_path = os.path.normpath(entry_relative_path)  # Normalize the path

            is_last = (index == total_entries - 1)
            connector = '└──' if is_last else '├──'

            # Enforce strict inclusion for directories
            if include_only:
                if entry_relative_path not in included_files and entry_relative_path not in included_dirs:
                    continue

            # Check for Git-ignored files and directories
            if ignore_gitignored and entry_relative_path in ignored_git_files:
                if display_gitignored_files:
                    if os.path.isdir(full_path):
                        tree_output += f"{prefix}{connector} {entry}/ # (Git-ignored)\n"
                    else:
                        tree_output += f"{prefix}{connector} {entry} # (Git-ignored)\n"
                continue  # Skip processing this entry

            # Check if file/directory is catgit-ignored
            if compiled_catgit_patterns and is_catgit_ignored(entry_relative_path, compiled_catgit_patterns):
                if display_catgitignored_files:
                    if os.path.isdir(full_path):
                        tree_output += f"{prefix}{connector} {entry}/ # (catgit-ignored)\n"
                    else:
                        tree_output += f"{prefix}{connector} {entry} # (catgit-ignored)\n"
                continue

            if os.path.isdir(full_path):
                tree_output += f"{prefix}{connector} {entry}/\n"
                traverse(full_path, prefix + ('    ' if is_last else '│   '), entry_relative_path)
            else:
                if entry in files_to_skip:
                    continue

                if is_text_file(full_path):
                    futures.append(executor.submit(process_file, full_path, extra_delimiter))
                    tree_output += f"{prefix}{connector} {entry}\n"
                else:
                    tree_output += f"{prefix}{connector} {entry} [Binary/Non-text]\n"

    with ThreadPoolExecutor(max_workers=8) as executor:
        traverse(path, relative_path='')

        # Collect the results from thread pool
        for future in futures:
            try:
                concatenated_output.append(future.result())
            except Exception as e:
                logger.error(f"Failed to process a file with threading: {e}")

    return tree_output, '\n'.join(concatenated_output)

# configure your default editor if not found
def configure_editor(config, config_path):
    """Prompt the user to configure a valid editor and update the configuration."""
    while True:
        editor = input("Enter a valid editor command (e.g., nano, vim, gedit) or press Enter to cancel: ").strip()
        if not editor:  # User cancels the input
            print("Editor setup canceled. Falling back to terminal output.")
            return None
        if check_editor_availability(editor):
            update_config(config_path, 'Defaults', 'editor_command', editor)
            print(f"Editor '{editor}' configured successfully.")
            return editor
        print(f"The editor '{editor}' is not available. Please try again.")

# main loop
def main():
    parser = argparse.ArgumentParser(description='Concatenate and display contents of a Git project.')
    
    # Optional Arguments
    parser.add_argument('--setup', action='store_true', help='Setup or modify the configuration')
    parser.add_argument('--editor', nargs='?', const=True, default=False, help='Directly open the output in an editor, optionally specify which editor')
    parser.add_argument('--include-only', '--included-only', '--includedonly', '--includeonly', '--onlyincluded', action='store_true', help='Only include files listed in the include file')
    parser.add_argument('--version', action='version', version=f'catgit {version_number} - https://github.com/FlyingFathead/catgit', help='Show the version number and exit')    

    # Positional Argument
    parser.add_argument('path', nargs='?', default='.', help='Path to the Git project root')

    args = parser.parse_args()

    if args.setup:
        setup_config()
        return

    config, config_path = load_config()

    # Configure logging based on debug_mode
    debug_mode = config.getboolean('Defaults', 'debug_mode')
    if debug_mode:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.WARNING

    # Reconfigure logging
    logging.basicConfig(level=logging_level, format='%(asctime)s - %(levelname)s - %(message)s')

    output_method = config['Defaults']['output_method']
    editor_command = config['Defaults']['editor_command']
    ignore_gitignored = config.getboolean('Defaults', 'ignore_gitignored')
    display_gitignored_files = config.getboolean('Defaults', 'display_gitignored_files')
    include_tree_view = config.getboolean('Defaults', 'include_tree_view_in_file')
    treat_non_git_as_error = config.getboolean('Defaults', 'treat_non_git_as_error')
    catgitignore_enabled = config.getboolean('Defaults', 'catgitignore_enabled')
    catgitignore_file = config['Defaults']['catgitignore_file']
    markup_catgitignored_files = config.getboolean('Defaults', 'markup_catgitignored_files')
    display_catgitignored_files = config.getboolean('Defaults', 'display_catgitignored_files')
    catgitinclude_enabled = config.getboolean('Defaults', 'catgitinclude_enabled')
    catgitinclude_file = config['Defaults']['catgitinclude_file']
    hide_nonexistent_gitignored = config.getboolean('Defaults', 'hide_nonexistent_gitignored')
    use_extra_delimiter = config.getboolean('Defaults', 'use_extra_delimiter')
    extra_delimiter_type = config['Defaults']['extra_delimiter_type']

    # Load and clean always_exclude_dirs
    always_exclude_dirs = [dir.strip() for dir in config.get('Defaults', 'always_exclude_dirs').split(',')]
    logger.debug(f"Always Exclude Dirs: {always_exclude_dirs}")

    # Set extra_delimiter to empty string if use_extra_delimiter is False
    extra_delimiter = extra_delimiter_type if use_extra_delimiter else ''

    if args.editor:
        if isinstance(args.editor, str):
            editor_command = args.editor
        output_method = 'editor'

    if output_method == 'editor' and not check_editor_availability(editor_command):
        print(f"The configured editor '{editor_command}' is not found.")
        new_editor = configure_editor(config, config_path)
        if new_editor:
            editor_command = new_editor
        else:
            output_method = 'terminal'

    if not is_git_repository(args.path):
        message = "The specified directory is not a Git repository."
        if treat_non_git_as_error:
            logger.error(message)
            return
        else:
            logger.warning(message)
            print("Warning: Operating in non-Git directory. Some features may not be available.")

    project_url = get_git_remote_url(args.path)

    include_only = args.include_only

    if include_only and catgitinclude_enabled:
        catgitinclude_path = os.path.join(args.path, catgitinclude_file)
        compiled_catgitinclude_patterns = parse_catgitinclude(catgitinclude_path)
        if not compiled_catgitinclude_patterns:
            print(f"No include patterns found in {catgitinclude_path}.")
            return
        included_files, included_dirs = get_included_files_and_dirs(args.path, compiled_catgitinclude_patterns)
    else:
        compiled_catgitinclude_patterns = None
        included_files = None
        included_dirs = None

    # Get .catgitignore patterns if enabled
    if catgitignore_enabled:
        catgitignore_path = os.path.join(args.path, catgitignore_file)
        compiled_catgit_patterns = parse_catgitignore(catgitignore_path)
    else:
        compiled_catgit_patterns = None

    # Retrieve all Git ignored files once
    if is_git_repository(args.path):
        ignored_git_files = get_all_git_ignored_files(args.path)
    else:
        ignored_git_files = set()

    tree_view = ""
    concatenated_output = ""
    if include_tree_view or output_method == 'terminal':
        # Generate tree view and concatenate file contents in a single traversal
        tree_view, concatenated_output = concatenate_and_generate_tree(
            args.path,
            ignored_git_files,
            compiled_catgit_patterns,
            include_tree_view,
            markup_catgitignored_files,
            display_catgitignored_files,
            always_exclude_dirs,
            ignore_gitignored,
            display_gitignored_files,
            include_only=include_only,
            included_files=included_files,
            included_dirs=included_dirs,
            hide_nonexistent_gitignored=hide_nonexistent_gitignored,
            extra_delimiter=extra_delimiter
        )

    # Generate the output string
    output = f"==== [ Project overview generated using `catgit` (v{version_number}) ] ====\n==== [ This directory tree's Git URL: {project_url} ] ====\n\n"
    if include_tree_view:
        if include_only:
            tree_header = "Directory structure (NOTE: `catgit` is in include-only mode, only these files from the directory tree are included):"
        else:
            tree_header = "Directory structure:"

        if use_extra_delimiter:
            output += f"{extra_delimiter}\n{tree_header}\n{tree_view}{extra_delimiter}\n\n"
        else:
            output += f"{tree_header}\n{tree_view}\n\n"

    if concatenated_output:
        output += concatenated_output

    if output_method == 'terminal':
        logger.info("Outputting to terminal...")
        print(output)
    elif output_method == 'editor':
        # Use tempfile to create a temporary file and open it with the specified editor
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w+') as tmpfile:
            tmpfile.write(output)
            tmpfile_path = tmpfile.name
        logger.info(f"Executing command: {editor_command} {tmpfile_path}")
        try:
            subprocess.run([editor_command, tmpfile_path], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Editor command failed: {e}")
            print(f"Failed to open editor: {e}")
    else:
        logger.debug("No output due to output method settings.")

if __name__ == '__main__':
    main()
