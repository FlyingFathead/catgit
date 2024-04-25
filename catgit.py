# catgit v0.04

import argparse
import subprocess
import os
import mimetypes
import configparser
from pathlib import Path

def load_config():
    config = configparser.ConfigParser()
    local_config_path = Path(__file__).parent / 'config.ini'
    global_config_path = Path.home() / '.config' / 'catgit' / 'config.ini'
    config.read_dict({'Defaults': {'output_method': 'terminal', 'editor_command': 'gedit'}})  # Set default values

    if local_config_path.exists():
        config.read(local_config_path)
    elif global_config_path.exists():
        config.read(global_config_path)
    else:
        os.makedirs(global_config_path.parent, exist_ok=True)
        with open(global_config_path, 'w') as configfile:
            config.write(configfile)

    return config

def main():
    config = load_config()
    parser = argparse.ArgumentParser(description='Concatenate and display contents of a Git project.')
    parser.add_argument('path', nargs='?', default='.', help='Path to the Git project root')
    args = parser.parse_args()

    if not is_git_repository(args.path):
        print("Error: The specified directory is not a Git repository.")
        return

    project_url = get_git_remote_url(args.path)
    output = f"Project URL: {project_url}\n\n"
    output += concatenate_project_files(args.path)
    
    if config['Defaults']['output_method'] == 'terminal':
        print(output)
    elif config['Defaults']['output_method'] == 'editor':
        temp_file_path = '/tmp/catgit_output.txt'
        with open(temp_file_path, 'w') as file:
            file.write(output)
        editor_command = config['Defaults']['editor_command']

        # Directly using os.system to see if the command executes normally
        command = f"{editor_command} {temp_file_path}"
        print(f"Executing command: {command}")
        os.system(command)

def is_git_repository(path):
    result = subprocess.run(['git', '-C', path, 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True)
    return result.returncode == 0

def get_git_remote_url(path):
    result = subprocess.run(['git', '-C', path, 'config', '--get', 'remote.origin.url'], capture_output=True, text=True)
    return result.stdout.strip()

def concatenate_project_files(path):
    output = ""
    base_length = len(path.rstrip(os.sep).split(os.sep))
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if d != '.git']
        dirs.sort()
        files.sort()
        relative_root = os.sep.join(root.split(os.sep)[base_length:])
        if relative_root:
            output += f"\n==== [ {relative_root}/ ] ====\n"
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = os.path.join(relative_root, file)
            if not is_ignored_by_git(full_path) and is_text_file(full_path):
                output += f"\n==== [ {relative_path} ] ====\n"
                with open(full_path, 'r', errors='ignore') as f:
                    output += f.read() + "\n"
            else:
                output += f"\n==== [ {relative_path} ] ==== SKIPPED (Binary or Ignored File)\n"
    return output

def is_ignored_by_git(file_path):
    result = subprocess.run(['git', 'check-ignore', file_path], capture_output=True)
    return result.returncode == 0

def is_text_file(file_path):
    type_hint, _ = mimetypes.guess_type(file_path)
    return 'text' in type_hint if type_hint else False

if __name__ == '__main__':
    main()
