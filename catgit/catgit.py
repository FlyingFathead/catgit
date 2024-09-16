# catgit
# https://github.com/FlyingFathead/catgit
# 2024 -/- FlyingFathead (w/ ChaosWhisperer)

version_number = "0.10.8"

import sys
import tempfile
import argparse
import subprocess
import os
import mimetypes
import configparser
import logging
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

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

    # Config paths // relative method
    # local_config_path = Path(__file__).parent / 'config.ini'
    # global_config_path = Path.home() / '.config' / 'catgit' / 'config.ini'            

    # Config paths
    script_dir = Path(__file__).resolve().parent
    local_config_path = script_dir / 'config.ini'
    global_config_path = Path.home() / '.config' / 'catgit' / 'config.ini'

    config = configparser.ConfigParser()
    config.read_dict({'Defaults': {
        'output_method': 'terminal',  # Default to terminal
        'editor_command': 'nano',  # Default to nano for editing
        'ignore_gitignored': 'true',  # Default to ignoring gitignored files
        'include_tree_view_in_file': 'true'  # Default to including tree view in the file output
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

def generate_tree_view(path, prefix='', ignore_gitignored=True):
    tree_output = ""
    try:
        entries = sorted(os.listdir(path))
    except OSError as e:
        logging.error("Error listing directory %s: %s", path, e)
        return ''

    for index, entry in enumerate(entries):
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path) and entry == '.git':
            continue  # Always skip .git directory

        if ignore_gitignored and is_ignored_by_git(full_path):
            continue  # Skip ignored files and directories

        connector = '├──' if index < len(entries) - 1 else '└──'
        if os.path.isdir(full_path):
            tree_output += f"{prefix}{connector} {entry}/\n"
            # Recursively generate tree view, appending output
            sub_tree = generate_tree_view(full_path, prefix + ('│   ' if index < len(entries) - 1 else '    '), ignore_gitignored)
            tree_output += sub_tree
        else:
            tree_output += f"{prefix}{connector} {entry}\n"

    return tree_output

def is_git_repository(path):
    try:
        result = subprocess.run(['git', '-C', path, 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True
        else:
            logging.error(f"Git check failed with message: {result.stderr.strip()}")
            return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command exception: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error checking Git repository: {e}")
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
            logging.info(f"No remote URL set for the repository at {path}.")
            return None
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed with error: {e.stderr}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error when trying to get git remote URL: {e}")
        return None

# testing with threading
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

# concatenate w/ threading
def concatenate_project_files_with_threads(path):
    """Use threads to process files and concatenate output."""
    output = []
    with ThreadPoolExecutor() as executor:
        futures = []
        for root, dirs, files in os.walk(path, topdown=True):
            dirs[:] = [d for d in dirs if d != '.git' and not is_ignored_by_git(os.path.join(root, d))]
            files = [f for f in files if not is_ignored_by_git(os.path.join(root, f)) and is_text_file(os.path.join(root, f))]
            for file in files:
                full_path = os.path.join(root, file)
                futures.append(executor.submit(process_file, full_path))
        for future in futures:
            try:
                output.append(future.result())
            except Exception as e:
                logging.error(f"Failed to process a file with threading: {e}")
    return ''.join(output)

# regular/old concatenate version (no threading)
def concatenate_project_files(path):
    output = ""
    logging.debug("Starting to concatenate files at %s", path)
    try:
        for root, dirs, files in os.walk(path, topdown=True):
            dirs[:] = [d for d in dirs if d != '.git' and not is_ignored_by_git(os.path.join(root, d))]
            files = [f for f in files if not is_ignored_by_git(os.path.join(root, f))]
            relative_root = os.path.relpath(root, start=path)

            if relative_root != '.':
                output += f"\n==== [ {relative_root}/ ] ====\n"
            for file in sorted(files):
                full_path = os.path.join(root, file)
                if is_text_file(full_path):
                    output += f"\n==== [ {file} ] ====\n"
                    with open(full_path, 'r', errors='ignore') as f:
                        file_contents = f.read()
                        output += file_contents + "\n"
                else:
                    output += f"\n==== [ {file} ] ==== SKIPPED (Binary or Ignored File)\n"
            logging.debug("Processed directory: %s", root)  # Debugging each directory processed

        logging.debug("Finished concatenating files. Output length: %d", len(output))
    except Exception as e:
        logging.error("Failed during file concatenation: %s", e)

    if not output:  # Check if output is empty
        logging.warning("Output is empty. No files were concatenated.")
    return output

def is_ignored_by_git(file_path):
    try:
        # Check if the file or directory is ignored by Git
        result = subprocess.run(['git', 'check-ignore', '-q', file_path],
                                capture_output=True, text=True)
        # -q option will not output anything to stdout or stderr, it will just set the exit status
        is_ignored = result.returncode == 0
        if is_ignored:
            logging.debug("Ignoring %s due to .gitignore rules.", file_path)
        else:
            logging.debug("%s is not ignored by .gitignore.", file_path)
        return is_ignored
    except subprocess.CalledProcessError as e:
        logging.error("Failed to check if %s is ignored by git: %s", file_path, e)
        return False  # Assume not ignored if there's an error checking

def is_text_file(file_path):
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
        logging.error(f"Zero division error when processing the file, skipping: {file_path}")
        return False  # Handle the division by zero explicitly
    except Exception as e:
        logging.error(f"Error reading {file_path}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Concatenate and display contents of a Git project.')
    parser.add_argument('path', nargs='?', default='.', help='Path to the Git project root')
    parser.add_argument('--setup', action='store_true', help='Setup or modify the configuration')
    parser.add_argument('--editor', nargs='?', const=True, default=False, help='Directly open the output in an editor, optionally specify which editor')
    parser.add_argument('--version', action='version', version=f'catgit {version_number} - https://github.com/FlyingFathead/catgit', help='Show the version number and exit')    
    args = parser.parse_args()

    if args.setup:
        setup_config()
        return

    config, config_path = load_config()
    output_method = config['Defaults']['output_method']
    editor_command = config['Defaults']['editor_command']
    ignore_gitignored = config.getboolean('Defaults', 'ignore_gitignored')
    include_tree_view = config.getboolean('Defaults', 'include_tree_view_in_file')
    treat_non_git_as_error = config.getboolean('Defaults', 'treat_non_git_as_error')

    if args.editor:
        output_method = 'editor'  # Override the output method to use the editor
        if isinstance(args.editor, str):
            editor_command = args.editor  # Use the specified editor from the command line

        # Check if the specified editor is available
        if not check_editor_availability(editor_command):
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
            logging.error(message)
            return
        else:
            logging.warning(message)
            print("Warning: Operating in non-Git directory. Some features may not be available.")
    
    project_url = get_git_remote_url(args.path)
    tree_view = generate_tree_view(args.path, ignore_gitignored=ignore_gitignored)

    # Generate the output string with or without the directory tree depending on config
    output = f"[ Project overview generated using `catgit` (v{version_number}) | Original Project URL: {project_url} ]\n\n"
    if include_tree_view:
        output += f"Directory structure:\n{tree_view}\n\n"
    
    # non-threaded (old version)
    # output += concatenate_project_files(args.path)

    # threaded concatenate
    output += concatenate_project_files_with_threads(args.path)

    if output_method == 'terminal':
        logging.info("Outputting to terminal...")
        print(output)
    elif output_method == 'editor':
        # Use tempfile to create a temporary file and open it with the specified editor
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w+') as tmpfile:
            tmpfile.write(output)
            tmpfile_path = tmpfile.name
        logging.info(f"Executing command: {editor_command} {tmpfile_path}")
        subprocess.run([editor_command, tmpfile_path], check=True)

    else:
        logging.debug("No output due to output method settings.")

if __name__ == '__main__':
    main()
