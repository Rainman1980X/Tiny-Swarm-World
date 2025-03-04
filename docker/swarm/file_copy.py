import os
import shutil
import subprocess

class FileSetup:
    def __init__(self, source_folder=None, dest_folder=None):
        """Initializes the file copying and permission setup."""
        self.source_folder = source_folder or os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        self.dest_folder = dest_folder or os.path.expanduser("~/setup_files")

    def run_command(self, command, error_message):
        """Executes a shell command and prints an error if it fails."""
        try:
            subprocess.run(command, shell=True, check=True, text=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"{error_message}\n{e.stderr}")
            exit(1)

    def copy_and_set_permissions(self):
        """Copies setup file_management and sets permissions."""
        if not os.path.exists(self.source_folder):
            print(f"Error: Source folder {self.source_folder} does not exist.")
            exit(1)

        print(f"Copying {self.source_folder} to {self.dest_folder}...")

        # Remove the destination folder if it already exists
        if os.path.exists(self.dest_folder):
            shutil.rmtree(self.dest_folder)

        # Copy the entire directory, including subdirectories
        shutil.copytree(self.source_folder, self.dest_folder, dirs_exist_ok=True)
        print("Files successfully copied!")

        print(f"Setting permissions for {self.dest_folder}...")
        self.run_command(f"sudo chown -R $USER:$USER {self.dest_folder}", "Error: Could not change ownership.")
        self.run_command(f"sudo chmod -R 755 {self.dest_folder}", "Error: Could not set permissions.")
        self.run_command(f"sudo find {self.dest_folder} -type f -name '*.sh' -exec chmod +x {{}} \\;", "Error: Could not make scripts executable.")

        print("Folder copied and permissions set successfully.")

    def full_setup(self):
        """Runs the entire file copying and permission setting process."""
        self.copy_and_set_permissions()


if __name__ == "__main__":
    setup = FileSetup()
    setup.full_setup()
