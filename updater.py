import os
import re
import shutil
import zipfile
import requests

"""
This script removes the open-source easycut and replaces it with the compiled version.
Run this script in the /home/pi/ directory.
"""

open_source_repo_owner = "BenjiPestell"
open_source_repo_name = "platform-distribution"

closed_source_repo_owner = "BenjiPestell"
closed_source_repo_name = "platform-distribution"

closed_source_directory = "easycut-new"
closed_source_executable = os.path.join(closed_source_directory, "new_easycut.exe")

# Open-source directories to backup from easycut-smartbench/src
backup_dir = "backup"
dirs_to_backup = ["jobCache", "sb_values"]

# When searching for the SW version file, search in these directories
search_directories = [".", closed_source_directory, "easycut-smartbench"]

# Pattern to match files like v2.8.1.txt or v3.12.1.txt (with or without extra text)
pattern_1 = re.compile(r'^v(\d+\.\d+\.\d+)(_.+)?\.txt$', re.IGNORECASE)

# Pattern to match files like v281.txt or v231.txt (with or without extra text)
pattern_2 = re.compile(r'^v(\d+\d+\d+)(_.+)?\.txt$', re.IGNORECASE)


def create_backup_directory():
    """Ensure the backup directory exists."""
    os.makedirs(backup_dir, exist_ok=True)


def backup_directory(source_path, summary):
    """Back up the specified directory to the backup folder."""
    create_backup_directory()

    dir_name = os.path.basename(source_path)
    destination_path = os.path.join(backup_dir, dir_name)

    try:
        shutil.copytree(source_path, destination_path)
        log_operation(summary, f"Backup of {dir_name}", "SUCCESS")
    except FileNotFoundError:
        log_operation(summary, f"Backup of {dir_name}", "FAILED (Not Found)")
    except Exception as e:
        log_operation(summary, f"Backup of {dir_name}", f"FAILED ({str(e)})")


def backup_file(source_path, summary):
    """Back up the specified file to the backup folder."""
    create_backup_directory()

    file_name = os.path.basename(source_path)
    destination_path = os.path.join(backup_dir, file_name)

    try:
        shutil.copy2(source_path, destination_path)
        log_operation(summary, f"Backup of {file_name}", "SUCCESS")
    except FileNotFoundError:
        log_operation(summary, f"Backup of {file_name}", "FAILED (Not Found)")
    except Exception as e:
        log_operation(summary, f"Backup of {file_name}", f"FAILED ({str(e)})")


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


def remove_file(filename, summary):
    """Remove the specified file."""

    for directory in search_directories:
        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                log_operation(summary, f"Removal of {filename}", "SUCCESS")
                return
            except FileNotFoundError:
                log_operation(summary, f"Removal of {filename}", "FAILED (Not Found)")
            except PermissionError:
                log_operation(summary, f"Removal of {filename}", "FAILED (Permission Denied)")
            except Exception as e:
                log_operation(summary, f"Removal of {filename}", f"FAILED ({str(e)})")
                return


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


def find_local_sw_version(summary, directory=os.getcwd()):
    """Find the SW version file in the specified directory."""

    if not os.path.exists(directory):
        return None

    # Search for the file in the current directory
    for directory in search_directories:
        if os.path.exists(directory):
            files = os.listdir(directory)
            for file in files:
                match_1 = pattern_1.match(file)
                match_2 = pattern_2.match(file)
                if match_1:
                    # Extract the version part from the filename
                    sw_version = match_1.group(1)
                    sw_version_string = f"v{sw_version}"
                    log_operation(summary, f"SW Version {sw_version_string} File", "FOUND")
                    return sw_version_string
                elif match_2:
                    # Extract the version part from the filename
                    sw_version = match_2.group(1)
                    sw_version_string = "v" + ".".join([sw_version[i:i + 1] for i in range(0, len(sw_version), 1)])
                    log_operation(summary, f"SW Version {sw_version_string} File", "FOUND")
                    return sw_version_string

    log_operation(summary, "SW Version File", "NOT FOUND. Assuming v0.0.0")
    return "v0.0.0"


def download_assets_from_tag(owner, repo, tag_name, directory, summary, extract_zips=True):
    """
    Download all assets associated with a given tag and save them in the current directory.
    Optionally, extract zip files.
    """

    if not os.path.exists(directory):
        os.makedirs(directory)

    url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag_name}"
    response = requests.get(url)

    if response.status_code == 200:
        release = response.json()
        assets = release.get('assets', [])

        if not assets:
            print("No assets found for the given tag.")
            return

        for asset in assets:
            asset_name = asset['name']
            download_url = asset['browser_download_url']

            print(f"Downloading {asset_name}...")

            # Stream the download to avoid loading it all in memory
            asset_path = os.path.join(directory, asset_name)
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(asset_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # Extract zip files if extract_zips is True
            if extract_zips and asset_name.endswith('.zip'):
                # noinspection PyTypeChecker
                with zipfile.ZipFile(asset_path, 'r') as zip_ref:
                    zip_ref.extractall(directory)
                os.remove(os.path.join(directory, asset_name))

        log_operation(summary, "Download content from tag", "SUCCESS")

    else:
        response.raise_for_status()


def retrieve_sw_version_file(source_path, summary):
    """Retrieve the SW version file from the specified directory."""
    if os.path.exists(source_path):
        files = os.listdir(source_path)
        for file in files:
            match_1 = pattern_1.match(file)
            match_2 = pattern_2.match(file)
            if match_1 or match_2:
                # Copy the file to the closed-source directory
                shutil.copy2(os.path.join(source_path, file), os.path.join(closed_source_directory, file))
                log_operation(summary, f"Retrieve {file}", "SUCCESS")
                return


def log_operation(summary, operation, result, print_realtime=False):
    """Log the result of an operation."""
    message = f"{operation}: {result}"
    summary.append(message)
    if print_realtime:
        print(message)


def print_summary(summary):
    """Print a summary of all operations."""
    if summary:
        print("\nSummary of Operations:")
    success_count = sum(1 for item in summary if ("FAIL" not in item and "NOT" not in item) or "CREATED" in item or "Assuming" in item)

    for item in summary:
        print(item)

    print(f"\n{success_count}/{len(summary)} operations successful.")


def update():
    summary = []
    backed_up_files = []
    fetch_new_start_easycut_script = False

    # Determine installed sw version from [sw_version].txt
    installed_sw_version = find_local_sw_version(summary)

    if installed_sw_version == "v0.0.0":
        fetch_new_start_easycut_script = True

    # Fetch latest tag from GitHub
    available_sw_version = get_latest_tag(closed_source_repo_owner, closed_source_repo_name, summary)

    # Compare installed and available SW versions
    a, b, c = map(int, installed_sw_version[1:].split("."))
    d, e, f = map(int, available_sw_version[1:].split("."))
    new_version_available = (a < d) or (a == d and b < e) or (a == d and b == e and c < f)
    ahead_of_remote = (a > d) or (a == d and b > e) or (a == d and b == e and c > f)
    if ahead_of_remote:
        print("SW is ahead of remote. How have you managed that?? - Exiting")
        return summary
    if not new_version_available:
        print("SW is up to date - Exiting")
        return summary

    # Check if old open-source easycut directory exists
    if os.path.exists("easycut-smartbench"):
        log_operation(summary, "Open-Source Easycut Directory", "FOUND")

        # Perform backups
        for directory in dirs_to_backup:
            backup_directory(os.path.join("easycut-smartbench", "src", directory), summary)

        # Remove open-source easycut directory
        remove_directory("easycut-smartbench", summary)

        # Replace the start_easycut.sh script
        fetch_new_start_easycut_script = True

    # Check if new compiled easycut directory exists
    if os.path.exists(closed_source_directory):
        log_operation(summary, "Compiled Easycut", "FOUND")

        # Backup and delete current version
        backup_file(closed_source_executable, summary)
        remove_file(closed_source_executable, summary)
    else:
        # Create new compiled easycut directory
        os.makedirs(closed_source_directory)
        log_operation(summary, "Compiled Easycut directory", "NOT FOUND, CREATED")

    # New version available, perform update
    log_operation(summary, "Newer Version Available", "YES")

    # Download and install new version
    download_assets_from_tag(open_source_repo_owner, open_source_repo_name, available_sw_version,
                             closed_source_directory, summary)

    # Replace the start_easycut.sh script if necessary
    if fetch_new_start_easycut_script:
        replace_file(os.path.join(closed_source_directory, "assets", "start_easycut.sh"), "start_easycut.sh", summary)

    # Fetch new SW version file
    retrieve_sw_version_file(os.path.join(closed_source_directory, "assets"), summary)

    # Delete old version file
    remove_file(f"{installed_sw_version.replace('.', '')}.txt", summary)

    # Position any backed-up files from open-source easycut
    if os.path.exists(backup_dir):
        for file in os.listdir(backup_dir):
            if not file.endswith(".exe"):  # Skip the backup of the closed-source executable
                shutil.move(os.path.join(backup_dir, file), os.path.join(closed_source_directory, file))
                backed_up_files.append(file)
    if backed_up_files:
        log_operation(summary, "Backed-Up & Positioned Files", ", ".join(backed_up_files))

    # Delete backup directory
    remove_directory(backup_dir, summary)

    return summary


if __name__ == "__main__":
    progress = update()
    print_summary(progress)
    input("Press Enter to exit...")
