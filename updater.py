import os
import re
import shutil

import requests

"""
This script removes the open-source easycut and replaces it with the compiled version.
Run this script in the /home/pi/ directory.
"""

close_source_repo_owner = "BenjiPestell"
close_source_repo_name = "platform-distribution"


def create_backup_directory():
    """Ensure the backup directory exists."""
    os.makedirs("backup", exist_ok=True)


def backup_directory(source_path, summary):
    """Back up the specified directory to the backup folder."""
    create_backup_directory()

    dir_name = os.path.basename(source_path)
    destination_path = os.path.join("backup", dir_name)

    try:
        shutil.copytree(source_path, destination_path)
        log_operation(summary, f"Backup of {dir_name}", "SUCCESS")
    except FileNotFoundError:
        log_operation(summary, f"Backup of {dir_name}", "FAILED (Not Found)")
    except Exception as e:
        log_operation(summary, f"Backup of {dir_name}", f"FAILED ({str(e)})")


def replace_file(source_path, destination_path, summary):
    """Replace the destination file with the source file."""
    try:
        shutil.copy2(source_path, destination_path)
        log_operation(summary, f"Replacement of {destination_path}", "SUCCESS")
    except FileNotFoundError:
        log_operation(summary, f"Replacement of {destination_path}", "FAILED (Source Not Found)")
    except Exception as e:
        log_operation(summary, f"Replacement of {destination_path}", f"FAILED ({str(e)})")


def remove_directory(directory_path, summary):
    """Remove the specified directory."""
    try:
        shutil.rmtree(directory_path)
        log_operation(summary, f"Removal of {directory_path}", "SUCCESS")
    except FileNotFoundError:
        log_operation(summary, f"Removal of {directory_path}", "FAILED (Not Found)")
    except PermissionError:
        log_operation(summary, f"Removal of {directory_path}", "FAILED (Permission Denied)")
    except Exception as e:
        log_operation(summary, f"Removal of {directory_path}", f"FAILED ({str(e)})")


def remove_file(file_path, summary):
    """Remove the specified file."""
    try:
        os.remove(file_path)
        log_operation(summary, f"Removal of {file_path}", "SUCCESS")
    except FileNotFoundError:
        log_operation(summary, f"Removal of {file_path}", "FAILED (Not Found)")
    except PermissionError:
        log_operation(summary, f"Removal of {file_path}", "FAILED (Permission Denied)")
    except Exception as e:
        log_operation(summary, f"Removal of {file_path}", f"FAILED ({str(e)})")


def get_latest_tag(owner, repo, summary):
    """Get the latest tag of a GitHub repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/tags"
    response = requests.get(url)

    if response.status_code == 200:
        tags = response.json()
        if tags:
            latest_tag = tags[0]['name']
            log_operation(summary, "Found latest tag: ", latest_tag)
            return latest_tag
        else:
            log_operation(summary, "Found latest tag: ", "None")
            return None
    else:
        log_operation(summary, "Get latest tag", f"FAILED ({response.status_code})")
        response.raise_for_status()


def find_local_sw_version(summary, directory="."):
    # Define the pattern to match files like v2.8.1.txt or v3.12.1.txt
    pattern = re.compile(r'^v(\d+\.\d+\.\d+)\.txt$', re.IGNORECASE)

    # Search for the file in the specified directory
    for root, dirs, files in os.walk(directory):
        for file in files:
            match = pattern.match(file)
            if match:
                # Extract the version part from the filename
                sw_version = match.group(1)
                log_operation(summary, f"SW Version {sw_version} File", "FOUND")
                return sw_version

    log_operation(summary, "SW Version File", "NOT FOUND")
    return None


def log_operation(summary, operation, result, print_realtime=False):
    """Log the result of an operation."""
    message = f"{operation}: {result}"
    summary.append(message)
    if print_realtime:
        print(message)


def print_summary(summary):
    """Print a summary of all operations."""
    if summary:
        print("Summary of Operations:")
    success_count = sum(1 for item in summary if "FAIL" not in item)

    for item in summary:
        print(item)

    print(f"\n{success_count}/{len(summary)} operations successful.")


def update():
    summary = []

    # Old open-source easycut directory exists
    if os.path.exists("easycut-smartbench"):
        log_operation(summary, "Open-Source Easycut Directory", "FOUND", True)

        # Perform backups
        backup_directory(os.path.join("easycut-smartbench", "src", "jobCache"), summary)
        backup_directory(os.path.join("easycut-smartbench", "src", "sb_values"), summary)

        # Remove open-source easycut directory
        remove_directory("easycut-smartbench", summary)

        # Replace the start_easycut.sh script
        replace_file(os.path.join("new", "start_easycut.sh"), "start_easycut.sh", summary)
        remove_directory("new", summary)

    # New compiled easycut directory exists
    if os.path.exists("main.exe"):
        log_operation(summary, "Compiled Easycut", "FOUND", True)

        # Determine installed sw version from [sw_version].txt
        installed_sw_version = find_local_sw_version(summary)
        if not installed_sw_version:
            return summary

        # Fetch latest tag from GitHub
        available_sw_version = get_latest_tag("yetitool", "easycut-smartbench", summary)

        a, b, c = map(int, installed_sw_version.split("."))
        d, e, f = map(int, available_sw_version.split("."))

        new_version_available = (a < d) or (a == d and b < e) or (a == d and b == e and c < f)

        # Check if newer version is available
        if new_version_available:
            log_operation(summary, "Newer Version Available", "YES")

            # Backup current version
            backup_directory("main.exe", summary)

            # Remove current version
            remove_file("main.exe", summary)

            # Download and install new version
            # download_new_version(available_sw_version, summary)

        else:
            print("SW is up to date")
            return summary

    return summary


if __name__ == "__main__":
    progress = []
    latest_tag = get_latest_tag(close_source_repo_owner, close_source_repo_name, progress)
    # progress = update()
    print_summary(progress)
    input("Press Enter to exit...")
