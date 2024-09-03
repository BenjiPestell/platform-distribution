import os
import shutil

"""
This script removes the open-source easycut and replaces it with the compiled version.
Run this script in the /home/pi/ directory.
"""


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


def log_operation(summary, operation, result, print_message=False):
    """Log the result of an operation."""
    message = f"{operation}: {result}"
    summary.append(message)
    if print_message:
        print(message)


def print_summary(summary):
    """Print a summary of all operations."""
    print("Summary of Operations:")
    success_count = sum(1 for item in summary if "SUCCESS" in item)

    for item in summary:
        print(item)

    print(f"\n{success_count}/{len(summary)} operations successful.")


def main():
    summary = []

    # Perform backups
    backup_directory(os.path.join("easycut-smartbench", "src", "jobCache"), summary)
    backup_directory(os.path.join("easycut-smartbench", "src", "sb_values"), summary)

    # Remove open-source easycut directory
    remove_directory("easycut-smartbench", summary)

    # Replace the start_easycut.sh script
    replace_file(os.path.join("new", "start_easycut.sh"), "start_easycut.sh", summary)
    remove_directory("new", summary)

    # Print summary of all operations
    print_summary(summary)

    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
