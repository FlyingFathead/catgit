# catgit v0.05
# https://github.com/FlyingFathead/catgit
# 2024 -/- FlyingFathead (w/ ChaosWhisperer)

import argparse
import subprocess
import os
import mimetypes
import configparser
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def load_config():
    config = configparser.ConfigParser()
    config.read_dict({'Defaults': {
        'output_method': 'terminal',  # Default
        'editor_command': 'gedit',
        'ignore_gitignored': 'true'
    }})

    local_config_path = Path(__file__).parent / 'config.ini'
    global_config_path = Path.home() / '.config' / 'catgit' / 'config.ini'
    read_files = config.read([str(local_config_path), str(global_config_path)])
    logging.debug("Config files read: %s", read_files)
    logging.debug("Output method from config: %s", config['Defaults']['output_method'])
    return config

def main():
    config = load_config()
    output_method = config['Defaults']['output_method']
    ignore_gitignored = config.getboolean('Defaults', 'ignore_gitignored')

    logging.info("Configured output method: %s", output_method)
    logging.info("Ignore .gitignored: %s", ignore_gitignored)

    parser = argparse.ArgumentParser(description='Concatenate and display contents of a Git project.')
    parser.add_argument('path', nargs='?', default='.', help='Path to the Git project root')
    args = parser.parse_args()

    if not is_git_repository(args.path):
        logging.error("The specified directory is not a Git repository.")
        return

    project_url = get_git_remote_url(args.path)
    logging.info("Project URL: %s", project_url)

    tree_view = generate_tree_view(args.path, ignore_gitignored=ignore_gitignored)
    logging.info("\nDirectory structure:\n%s", tree_view)

    # Here is the corrected line
    output = f"Project URL: {project_url}\n\n" + concatenate_project_files(args.path)
    if output_method == 'terminal':
        logging.info("Outputting to terminal...")
        print(output)
    else:
        logging.debug("Output method is not terminal, output is not printed.")

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
    type_hint, _ = mimetypes.guess_type(file_path)
    return 'text' in type_hint if type_hint else False

if __name__ == '__main__':
    main()
