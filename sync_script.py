import os
import schedule
import time
import requests
from requests.auth import HTTPBasicAuth

# Load WebDAV configuration from environment variables
options = {
    'webdav_hostname': os.getenv("WEBDAV_HOSTNAME", "https://webdav.myserver.io"),
    'webdav_login': os.getenv("WEBDAV_LOGIN"),
    'webdav_password': os.getenv("WEBDAV_PASSWORD")
}

# Directories
def normalize_path(path):
    return path.rstrip('/') + '/'

remote_dir = normalize_path(os.getenv("REMOTE_DIR", "/remote_folder"))
local_dir = os.getenv("LOCAL_DIR", "/app/data")  # Mount this to a NAS directory

# Run mode and schedule
run_mode = os.getenv("RUN_MODE", "scheduled")  # "manual" or "scheduled"
scheduled_time = os.getenv("SCHEDULED_TIME", "02:00")  # Default to 2 AM
cleanup_enabled = os.getenv("CLEANUP_ENABLED", "true").lower() == "true"  # Convert to boolean

# Function to send a PROPFIND request and list directory contents
def list_directory(url, username, password):
    try:
        headers = {"Depth": "1"}
        response = requests.request("PROPFIND", url, auth=HTTPBasicAuth(username, password), headers=headers)
        if response.status_code != 207:
            print(f"Failed to list directory: {url}, Status Code: {response.status_code}")
            return []

        # Parse the response to extract file names
        from xml.etree import ElementTree as ET
        tree = ET.fromstring(response.text)
        namespaces = {'D': 'DAV:'}
        files = []
        for response in tree.findall("D:response", namespaces):
            href = response.find("D:href", namespaces).text
            if not href.endswith("/"):  # Exclude directories
                files.append(href.split("/")[-1])
        return files
    except Exception as e:
        print(f"Error listing directory: {e}")
        return []

# Function to sync files
def sync_files():
    try:
        print(f"Normalized remote directory: {remote_dir}")
        print(f"Connecting to: {options['webdav_hostname']}, with username: {options['webdav_login']}")

        # List files in the remote directory
        remote_files = list_directory(f"{options['webdav_hostname']}{remote_dir}", options['webdav_login'], options['webdav_password'])
        print(f"Found remote files: {remote_files}")

        for file in remote_files:
            local_path = os.path.join(local_dir, file)
            if not os.path.exists(local_path):
                print(f"Downloading {file}...")
                download_file(f"{remote_dir}{file}", local_path)
    except Exception as e:
        print(f"Error syncing files: {e}")

# Function to download files
def download_file(remote_path, local_path):
    try:
        url = f"{options['webdav_hostname']}{remote_path}"
        response = requests.get(url, auth=HTTPBasicAuth(options['webdav_login'], options['webdav_password']), stream=True)
        if response.status_code == 200:
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded {local_path}")
        else:
            print(f"Failed to download {remote_path}: {response.status_code}")
    except Exception as e:
        print(f"Error downloading file {remote_path}: {e}")

# Function to clean up files
def cleanup_files():
    if not cleanup_enabled:
        return

    try:
        for root, _, files in os.walk(local_dir):
            for file in files:
                if not file.endswith(('.mp4', '.srt')):
                    file_path = os.path.join(root, file)
                    print(f"Removing {file_path}...")
                    os.remove(file_path)
    except Exception as e:
        print(f"Error during cleanup: {e}")

# Run sync and cleanup tasks
def run_tasks():
    print(f"Starting tasks at {time.strftime('%Y-%m-%d %H:%M:%S')}...")
    sync_files()
    cleanup_files()

# Schedule tasks
if run_mode == "scheduled":
    schedule.every().day.at(scheduled_time).do(run_tasks)
    print(f"Scheduled tasks to run daily at {scheduled_time}.")

# Manual execution
if __name__ == "__main__":
    if run_mode == "manual":
        run_tasks()  # Run immediately for testing
    else:
        # Run scheduled tasks
        while True:
            schedule.run_pending()
            time.sleep(1)
