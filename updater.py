import os
import sys
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

default_sw_version = "v0.0.0"

open_source_directory = "easycut-smartbench"

# Essential basic requirements
basic_requirements = ["start_easycut.sh"]

# Open-source directories to backup from easycut-smartbench/src
backup_dir = "backup"
dirs_to_backup = ["jobCache", "sb_values"]

# When searching for the SW version file, search in these directories
search_directories = [".", closed_source_directory, "easycut-smartbench"]

# Pattern to match files like v2.8.1.txt or v3.12.1.txt (with or without extra text)
sw_filename_pattern_1 = re.compile(r'^v(\d+\.\d+\.\d+)(_.+)?\.txt$', re.IGNORECASE)

# Pattern to match files like v281.txt or v231.txt (with or without extra text)
sw_filename_pattern_2 = re.compile(r'^v(\d+\d+\d+)(_.+)?\.txt$', re.IGNORECASE)

summary = []


class GitHub(object):
    def __init__(self, owner, repo):
        self.owner = owner
        self.repo = repo

    def get_sw_version(self, *kwargs):
        return self.get_latest_tag(*kwargs)

    def get_latest_tag(self, owner=None, repo=None):
        """Get the latest tag of a GitHub repository."""

        owner = owner or self.owner
        repo = repo or self.repo

        url = f"https://api.github.com/repos/{owner}/{repo}/tags"
        response = requests.get(url)

        if response.status_code == 200:
            tags = response.json()
            if tags:
                latest_tag = tags[0]['name']
                log_operation("Found latest tag: ", latest_tag)
                return latest_tag
            else:
                log_operation("Found latest tag: ", "None", critical=True)
                return None
        else:
            log_operation("Get latest tag", f"FAILED ({response.status_code})", critical=True)
            response.raise_for_status()

    def download_content(self, owner=None, repo=None, tag_name=None, directory=None, extract_zips=True):
        """
        Download all content associated with a given tag and save them in the current directory.
        Optionally, extract zip files.
        """

        owner = owner or self.owner
        repo = repo or self.repo

        if not os.path.exists(directory):
            os.makedirs(directory)

        url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag_name}"
        response = requests.get(url)

        if response.status_code == 200:
            release = response.json()
            assets = release.get('assets', [])

            if not assets:
                log_operation("Download content from tag", "FAILED (No assets found)")
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

            log_operation("Download content from tag", "SUCCESS")

        else:
            response.raise_for_status()


class USB_Storage(object):
    windows_usb_path = "E:\\"
    linux_usb_path = "/media/usb/"

    def __int__(self):
        if sys.platform == "win32":
            self.usb_path = self.windows_usb_path
        else:
            self.usb_path = self.linux_usb_path

    def is_available(self):
        return os.path.exists(self.usb_path)

    def get_sw_version(self):
        if not self.is_available():
            return None

        for file in os.listdir(self.usb_path):
            match_1 = sw_filename_pattern_1.match(file)
            match_2 = sw_filename_pattern_2.match(file)
            if match_1:
                # Extract the version part from the filename
                sw_version = match_1.group(1)
                sw_version_string = f"v{sw_version}"
                log_operation(f"USB SW Version {sw_version_string} File", "FOUND")
                return sw_version_string
            elif match_2:
                # Extract the version part from the filename
                sw_version = match_2.group(1)
                sw_version_string = "v" + ".".join([sw_version[i:i + 1] for i in range(0, len(sw_version), 1)])
                log_operation(f"USB SW Version {sw_version_string} File", "FOUND")
                return sw_version_string

        log_operation("USB SW Version File", "NOT FOUND")
        return None

    def download_content(self, directory=None, extract_zips=True):
        directory = directory or closed_source_directory

        if not self.is_available():
            return

        for file in os.listdir(self.usb_path):
            shutil.copy2(os.path.join(self.usb_path, file), closed_source_directory)

            # Extract zip files if extract_zips is True
            if extract_zips and file.endswith('.zip'):
                # noinspection PyTypeChecker
                with zipfile.ZipFile(file, 'r') as zip_ref:
                    zip_ref.extractall(directory)
                os.remove(os.path.join(directory, file))


def create_backup_directory():
    """Ensure the backup directory exists."""
    os.makedirs(backup_dir, exist_ok=True)


def backup_directory(source_path):
    """Back up the specified directory to the backup folder."""
    create_backup_directory()

    dir_name = os.path.basename(source_path)
    destination_path = os.path.join(backup_dir, dir_name)

    try:
        shutil.copytree(source_path, destination_path)
        log_operation(f"Backup of {dir_name}", "SUCCESS")
    except FileNotFoundError:
        log_operation(f"Backup of {dir_name}", "FAILED (Not Found)", critical=True)
    except Exception as e:
        log_operation(f"Backup of {dir_name}", f"FAILED ({str(e)})", critical=True)


def backup_file(source_path):
    """Back up the specified file to the backup folder."""
    create_backup_directory()

    file_name = os.path.basename(source_path)
    destination_path = os.path.join(backup_dir, file_name)

    try:
        shutil.copy2(source_path, destination_path)
        log_operation(f"Backup of {file_name}", "SUCCESS")
    except FileNotFoundError:
        log_operation(f"Backup of {file_name}", "FAILED (Not Found)", critical=True)
    except Exception as e:
        log_operation(f"Backup of {file_name}", f"FAILED ({str(e)})", critical=True)


def replace_file(source_path, destination_path):
    """Replace the destination file with the source file."""
    try:
        shutil.copy2(source_path, destination_path)
        log_operation(f"Replacement of {destination_path}", "SUCCESS")
    except FileNotFoundError:
        log_operation(f"Replacement of {destination_path}", "FAILED (Source Not Found)", critical=True)
    except Exception as e:
        log_operation(f"Replacement of {destination_path}", f"FAILED ({str(e)})", critical=True)


def remove_directory(directory_path):
    """Remove the specified directory."""
    try:
        shutil.rmtree(directory_path)
        log_operation(f"Removal of {directory_path}", "SUCCESS")
    except FileNotFoundError:
        log_operation(f"Removal of {directory_path}", "FAILED (Not Found)")
    except PermissionError:
        log_operation(f"Removal of {directory_path}", "FAILED (Permission Denied)", critical=True)
    except Exception as e:
        log_operation(f"Removal of {directory_path}", f"FAILED ({str(e)})", critical=True)


def remove_file(filename):
    """Remove the specified file."""

    for directory in search_directories:
        file_path = os.path.join(directory, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                log_operation(f"Removal of {filename}", "SUCCESS")
                return
            except FileNotFoundError:
                log_operation(f"Removal of {filename}", "FAILED (Not Found)")
            except PermissionError:
                log_operation(f"Removal of {filename}", "FAILED (Permission Denied)", critical=True)
            except Exception as e:
                log_operation(f"Removal of {filename}", f"FAILED ({str(e)})", critical=True)
                return


def find_local_sw_version(directory=os.getcwd()):
    """Find the SW version file in the specified directory."""

    if not os.path.exists(directory):
        return None

    # Search for the file in the current directory
    for directory in search_directories:
        if os.path.exists(directory):
            files = os.listdir(directory)
            for file in files:
                match_1 = sw_filename_pattern_1.match(file)
                match_2 = sw_filename_pattern_2.match(file)
                if match_1:
                    # Extract the version part from the filename
                    sw_version = match_1.group(1)
                    sw_version_string = f"v{sw_version}"
                    log_operation(f"SW Version {sw_version_string} File", "FOUND")
                    return sw_version_string
                elif match_2:
                    # Extract the version part from the filename
                    sw_version = match_2.group(1)
                    sw_version_string = "v" + ".".join([sw_version[i:i + 1] for i in range(0, len(sw_version), 1)])
                    log_operation(f"SW Version {sw_version_string} File", "FOUND")
                    return sw_version_string

    log_operation("SW Version File", "NOT FOUND. Assuming {}".format(default_sw_version))
    return default_sw_version


def retrieve_sw_version_file(source_path):
    """Retrieve the SW version file from the specified directory."""
    if os.path.exists(source_path):
        files = os.listdir(source_path)
        for file in files:
            match_1 = sw_filename_pattern_1.match(file)
            match_2 = sw_filename_pattern_2.match(file)
            if match_1 or match_2:
                # Copy the file to the closed-source directory
                shutil.copy2(os.path.join(source_path, file), os.path.join(closed_source_directory, file))
                log_operation(f"Retrieve {file}", "SUCCESS")
                return


def log_operation(operation, result, critical=False, print_realtime=False):
    """Log the result of an operation."""
    critical_message = "CRITICAL: " if critical else ""
    message = f"{critical_message}{operation}: {result}"
    summary.append(message)
    if print_realtime:
        print(message)


def print_summary():
    """Print a summary of all operations."""
    if summary:
        print("\nSummary of Operations:")
    critical_count = sum("CRITICAL" in item for item in summary)
    success_count = len(summary) - critical_count

    for item in summary:
        print(item)

    print(f"\n{success_count}/{len(summary)} operations successful.")


def update():
    usb = USB_Storage()

    # Check if the USB storage is available, otherwise use GitHub
    if usb.is_available():
        log_operation("USB Storage", "FOUND", print_realtime=True)
        update_source = usb
    else:
        log_operation("USB Storage", "NOT FOUND", critical=False, print_realtime=True)
        update_source = GitHub(closed_source_repo_owner, closed_source_repo_name)

    # Determine the currently installed SW version
    local_sw_version = find_local_sw_version()

    # Determine the latest available SW version
    latest_sw_version = update_source.get_sw_version()

    # Compare installed and available SW versions
    a, b, c = map(int, local_sw_version[1:].split("."))
    d, e, f = map(int, latest_sw_version[1:].split("."))

    new_version_available = (a < d) or (a == d and b < e) or (a == d and b == e and c < f)
    ahead_of_remote = (a > d) or (a == d and b > e) or (a == d and b == e and c > f)

    # Check for basic requirements
    basic_requirements_met = True
    for file in basic_requirements:
        if os.path.exists(file):
            log_operation(f"Basic Requirement {file}", "FOUND")
        else:
            basic_requirements_met = False
            log_operation(f"Basic Requirement {file}", "NOT FOUND", critical=True)

    if ahead_of_remote:
        print("SW is ahead of remote. How have you managed that?? - Exiting")
        return

    if not new_version_available and basic_requirements_met:
        print("SW is up to date - Exiting")

    # Check for old open-source directory
    if os.path.exists(open_source_directory):
        log_operation(f"Old Open-Source Directory {open_source_directory}", "FOUND")

        # Perform backups from src folder
        for directory in dirs_to_backup:
            backup_directory(os.path.join(open_source_directory, "src", directory))

        # Remove open-source easycut directory
        remove_directory("easycut-smartbench")

    # Download the latest SW version
    update_source.download_content()  # All this still needs to be positioned correctly


if __name__ == "__main__":
    update()
    print_summary()
    input("Press Enter to exit...")
