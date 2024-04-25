# catgit
# https://github.com/FlyingFathead/catgit
# 2024 -/- FlyingFathead (w/ ChaosWhisperer)

version_number = "0.10.3"

import sys
import tempfile
import argparse
import subprocess
import os
import mimetypes
import configparser
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')

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
    print("Current settings:")
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
        result = subprocess.run(['git', '-C', path, 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        logging.error(f"Git command failed: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
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
    args = parser.parse_args()

    if args.setup:
        setup_config()
        return

    config, config_path = load_config() 
    output_method = config['Defaults']['output_method']
    editor_command = config['Defaults']['editor_command']
    ignore_gitignored = config.getboolean('Defaults', 'ignore_gitignored')
    include_tree_view = config.getboolean('Defaults', 'include_tree_view_in_file')

    parser = argparse.ArgumentParser(description='Concatenate and display contents of a Git project.')
    parser.add_argument('path', nargs='?', default='.', help='Path to the Git project root')
    args = parser.parse_args()

    if not is_git_repository(args.path):
        logging.error("The specified directory is not a Git repository.")
        return

    project_url = get_git_remote_url(args.path)
    tree_view = generate_tree_view(args.path, ignore_gitignored=ignore_gitignored)

    # Generate the output string with or without the directory tree depending on config
    output = f"[ catgit v{version_number} | Project URL: {project_url} ]\n\n"
    if include_tree_view:
        output += f"Directory structure:\n{tree_view}\n\n"
    output += concatenate_project_files(args.path)

    if output_method == 'terminal':
        logging.info("Outputting to terminal...")
        print(output)
    elif output_method == 'editor':
        # Use tempfile to create a temporary file
        # 'delete=False' means the file will not be deleted when closed, allowing it to be opened by an editor
        with tempfile.NamedTemporaryFile(delete=False, suffix='.txt', mode='w+') as tmpfile:
            tmpfile.write(output)
            tmpfile_path = tmpfile.name  # Get the path of the temporary file

        logging.info(f"Executing command: {editor_command} {tmpfile_path}")
        os.system(f"{editor_command} {tmpfile_path}")

        # Optionally, you can remove the temp file if you don't want it to persist after opening
        # os.remove(tmpfile_path)

    else:
        logging.debug("No output due to output method settings.")

if __name__ == '__main__':
    main()
