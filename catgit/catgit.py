# catgit.py
# https://github.com/FlyingFathead/catgit
# 2024 -/- FlyingFathead (w/ ChaosWhisperer)

version_number = "0.11.1"

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
        'debug_mode': 'false'  # Default to false
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
        logger.warning(f"{catgitignore_path} not found.")
    except Exception as e:
        logger.error(f"Error reading {catgitignore_path}: {e}")
    logger.debug(f"Parsed .catgitignore with {len(patterns)} compiled patterns.")
    return patterns

def get_all_files(path):
    """Generator to yield all file paths relative to the root path."""
    for root, dirs, files in os.walk(path):
        for file in files:
            yield os.path.relpath(os.path.join(root, file), start=path)

def get_all_git_ignored_files(path):
    """Retrieve all Git ignored files in the repository."""
    ignored_files = set()
    try:
        # Use git check-ignore with --stdin and -z for null-separated output
        git_cmd = ['git', '-C', path, 'check-ignore', '-z', '--stdin']
        process = subprocess.Popen(git_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        all_files = '\0'.join(get_all_files(path))  # Corrected separator from '\n' to '\0'
        stdout, stderr = process.communicate(input=all_files)
        if process.returncode in [0, 1]:  # 0: some ignored files, 1: no ignored files
            ignored_files = set(stdout.strip().split('\0')) if stdout.strip() else set()
            # Removed os.path.relpath since paths are already relative
            ignored_files = {f for f in ignored_files if f}
            logger.debug(f"Retrieved {len(ignored_files)} Git ignored files.")
        else:
            logger.error(f"Git check-ignore failed with stderr: {stderr.strip()}")
    except Exception as e:
        logger.error(f"Error retrieving Git ignored files: {e}")
    return ignored_files

def is_catgit_ignored(relative_path, compiled_patterns):
    """Determine if a file should be ignored based on compiled .catgitignore patterns."""
    for pattern in compiled_patterns:
        if pattern.match(relative_path):
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

def process_file(full_path):
    """Process individual file to get content and metadata."""
    try:
        with open(full_path, 'r', errors='ignore') as file:
            content = file.read()
        file_size = os.stat(full_path).st_size
        num_lines = content.count('\n')
        return f"\n==== [ {full_path} | Size: {file_size} bytes | Lines: {num_lines} ] ====\n{content}\n"
    except Exception as e:
        return f"\n==== [ {full_path} ] ==== SKIPPED (Error: {str(e)})\n"

def concatenate_and_generate_tree(path, ignored_git_files, compiled_catgit_patterns, include_tree_view, 
                                 markup_catgitignored_files, display_catgitignored_files, always_exclude_dirs):
    """Traverse the directory once to generate tree view and concatenate file contents."""
    tree_output = ""
    concatenated_output = []
    futures = []
    files_to_skip = {'.gitignore', '.catgitignore'}

    def traverse(current_path, prefix=''):
        nonlocal tree_output, concatenated_output
        try:
            entries = sorted(os.listdir(current_path))
        except OSError as e:
            logger.error(f"Error listing directory {current_path}: {e}")
            return

        # Filter out always_exclude_dirs
        entries = [e for e in entries if not (os.path.isdir(os.path.join(current_path, e)) and e in always_exclude_dirs)]

        # Total entries count
        total_entries = len(entries)
        for index, entry in enumerate(entries):
            full_path = os.path.join(current_path, entry)
            relative_path = os.path.relpath(full_path, start=path)

            # Determine if it's the last entry
            is_last = (index == total_entries - 1)
            connector = '└──' if is_last else '├──'

            if os.path.isdir(full_path):
                # Exclude directories ignored by Git
                if relative_path in ignored_git_files:
                    continue  # Skip ignored directories

                # Exclude directories matched by .catgitignore
                if compiled_catgit_patterns and is_catgit_ignored(relative_path, compiled_catgit_patterns):
                    if display_catgitignored_files:
                        if markup_catgitignored_files:
                            tree_output += f"{prefix}{connector} # (catgit ignored) {entry}/\n"
                        else:
                            tree_output += f"{prefix}{connector} {entry}/\n"
                    continue

                # Add directory to tree view
                tree_output += f"{prefix}{connector} {entry}/\n"

                # Prepare the prefix for the next level
                extension = '    ' if is_last else '│   '

                # Recursive traversal
                traverse(full_path, prefix + extension)
            else:
                # Skip processing .gitignore and .catgitignore files
                if entry in files_to_skip:
                    continue

                # Exclude files ignored by Git
                if relative_path in ignored_git_files:
                    continue  # Skip ignored files

                # Check if file is ignored by .catgitignore
                if compiled_catgit_patterns and is_catgit_ignored(relative_path, compiled_catgit_patterns):
                    if display_catgitignored_files:
                        if markup_catgitignored_files:
                            tree_output += f"{prefix}{connector} # (catgit ignored) {entry}\n"
                        else:
                            tree_output += f"{prefix}{connector} {entry}\n"
                    continue

                # Determine if the file is a text file
                if is_text_file(full_path):
                    # Submit file processing to thread pool
                    futures.append(executor.submit(process_file, full_path))
                    # Add to tree view
                    tree_output += f"{prefix}{connector} {entry}\n"
                else:
                    # Binary or other non-text file
                    tree_output += f"{prefix}{connector} {entry} [Binary/Non-text]\n"

    with ThreadPoolExecutor(max_workers=8) as executor:
        traverse(path)

        # Collect the results from thread pool
        for future in futures:
            try:
                concatenated_output.append(future.result())
            except Exception as e:
                logger.error(f"Failed to process a file with threading: {e}")

    return tree_output, ''.join(concatenated_output)

def main():
    parser = argparse.ArgumentParser(description='Concatenate and display contents of a Git project.')
    
    # Optional Arguments
    parser.add_argument('--setup', action='store_true', help='Setup or modify the configuration')
    parser.add_argument('--editor', nargs='?', const=True, default=False, help='Directly open the output in an editor, optionally specify which editor')
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
    include_tree_view = config.getboolean('Defaults', 'include_tree_view_in_file')
    treat_non_git_as_error = config.getboolean('Defaults', 'treat_non_git_as_error')
    catgitignore_enabled = config.getboolean('Defaults', 'catgitignore_enabled')
    catgitignore_file = config['Defaults']['catgitignore_file']
    markup_catgitignored_files = config.getboolean('Defaults', 'markup_catgitignored_files')
    display_catgitignored_files = config.getboolean('Defaults', 'display_catgitignored_files')

    # Load and clean always_exclude_dirs
    always_exclude_dirs = [dir.strip() for dir in config.get('Defaults', 'always_exclude_dirs').split(',')]
    logger.debug(f"Always Exclude Dirs: {always_exclude_dirs}")

    if args.editor:
        if isinstance(args.editor, str):
            editor_command = args.editor
        output_method = 'editor'

    if args.editor and not check_editor_availability(editor_command):
        new_editor = get_valid_editor(editor_command)
        if new_editor:
            editor_command = new_editor
            update_config(config_path, 'Defaults', 'editor_command', new_editor)
        else:
            print("No valid editor provided, falling back to the terminal output.")
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
            always_exclude_dirs
        )

    # Generate the output string
    output = f"[ Project overview generated using `catgit` (v{version_number}) | Original Project URL: {project_url} ]\n\n"
    if include_tree_view:
        output += f"Directory structure:\n{tree_view}\n\n"

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
