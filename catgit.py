# catgit v0.02

import argparse
import subprocess
import os
import mimetypes

def main():
    parser = argparse.ArgumentParser(description='Concatenate and display contents of a Git project.')
    parser.add_argument('path', nargs='?', default='.', help='Path to the Git project root')
    args = parser.parse_args()

    if not is_git_repository(args.path):
        print("Error: The specified directory is not a Git repository.")
        return

    project_url = get_git_remote_url(args.path)
    output = f"Project URL: {project_url}\n\n"
    output += concatenate_project_files(args.path)
    
    print(output)  # Or handle according to user configuration

def is_git_repository(path):
    """Check if the directory is a git repository."""
    result = subprocess.run(['git', '-C', path, 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True)
    return result.returncode == 0

def get_git_remote_url(path):
    """Retrieve the remote URL of the git repository."""
    result = subprocess.run(['git', '-C', path, 'config', '--get', 'remote.origin.url'], capture_output=True, text=True)
    return result.stdout.strip()

def concatenate_project_files(path):
    output = ""
    base_length = len(path.rstrip(os.sep).split(os.sep))
    for root, dirs, files in os.walk(path, topdown=True):
        dirs[:] = [d for d in dirs if d != '.git']  # Skip .git directory
        # Sort directories and files to maintain a consistent order
        dirs.sort()
        files.sort()
        relative_root = os.sep.join(root.split(os.sep)[base_length:])
        if relative_root:
            output += f"\n==== [ {relative_root}/ ] ====\n"
        for file in files:
            full_path = os.path.join(root, file)
            relative_path = os.path.join(relative_root, file)
            if not is_ignored_by_git(full_path):
                if is_text_file(full_path):
                    output += f"\n==== [ {relative_path} ] ====\n"
                    with open(full_path, 'r', errors='ignore') as f:
                        output += f.read() + "\n"
                else:
                    output += f"\n==== [ {relative_path} ] ==== SKIPPED (Binary File)\n"
    return output

def is_ignored_by_git(file_path):
    result = subprocess.run(['git', 'check-ignore', file_path], capture_output=True)
    return result.returncode == 0

def is_text_file(file_path):
    type_hint, _ = mimetypes.guess_type(file_path)
    if type_hint and 'text' in type_hint:
        return True
    try:
        # Open the file in binary mode and read a small portion to check for non-text characters
        with open(file_path, 'rb') as f:
            return not bool(f.read(1024).translate(None, bytes(range(32, 127)) + b'\n\r\t\f\b'))
    except Exception as e:
        # Assume any files that cannot be opened are non-text
        return False

if __name__ == '__main__':
    main()

