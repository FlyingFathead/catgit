# catgit
# https://github.com/FlyingFathead/catgit
# 2024 -/- FlyingFathead (w/ ChaosWhisperer)

version_number = "0.10.1"

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

    # Config paths
    local_config_path = Path(__file__).parent / 'config.ini'
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
    result = subprocess.run(['git', '-C', path, 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True)
    return result.returncode == 0

def get_git_remote_url(path):
    result = subprocess.run(['git', '-C', path, 'config', '--get', 'remote.origin.url'], capture_output=True, text=True)
    return result.stdout.strip()

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
        # We consider a file to be text if more than 70% of its characters are printable text characters or whitespace
        if content:  # Check if file is not empty
            text_chars = {7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x7f))  # ASCII control characters and printable range
            nontext_char_count = sum(1 for byte in content if byte not in text_chars)
            percentage_of_text_chars = 100 * (1 - nontext_char_count / len(content))
            logging.debug("%s - Percentage of text characters: %.2f%%", file_path, percentage_of_text_chars)
            is_text = percentage_of_text_chars > 70
        else:
            is_text = True  # Empty files are considered text files

        logging.debug("File %s is considered %s", file_path, "text" if is_text else "non-text")
        return is_text
    except Exception as e:
        logging.error("Error reading %s: %s", file_path, str(e))
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
        temp_file_path = '/tmp/catgit_output.txt'
        with open(temp_file_path, 'w') as file:
            file.write(output)
        logging.info(f"Executing command: {editor_command} {temp_file_path}")
        os.system(f"{editor_command} {temp_file_path}")
    else:
        logging.debug("No output due to output method settings.")

if __name__ == '__main__':
    main()
