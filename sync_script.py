import os
import schedule
import time
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from pathlib import Path

# Load WebDAV configuration from environment variables
options = {
    'webdav_hostname': os.getenv("WEBDAV_HOSTNAME", "https://example.webdav.server"),
    'webdav_login': os.getenv("WEBDAV_LOGIN"),
    'webdav_password': os.getenv("WEBDAV_PASSWORD")
}

# Directories
def normalize_path(path):
    return path.rstrip('/') + '/'

remote_dir = normalize_path(os.getenv("REMOTE_DIR", "/remote_folder"))
local_dir = normalize_path(os.getenv("LOCAL_DIR", "/app/data"))

# Sync mode and file type filtering
sync_mode = os.getenv("SYNC_MODE", "remote-to-local")  # remote-to-local, local-to-remote, or two-way
include_file_types = os.getenv("INCLUDE_FILE_TYPES", "").split(",")  # e.g., "mp4,srt"
exclude_file_types = os.getenv("EXCLUDE_FILE_TYPES", "").split(",")  # e.g., "txt,tmp"

# Scheduling
run_mode = os.getenv("RUN_MODE", "scheduled")  # manual or scheduled
scheduled_time = os.getenv("SCHEDULED_TIME", "02:00")  # Default sync time

# Function to check if a file matches the include/exclude filters
def file_matches_filters(file_name):
    # Allow all files if both filters are empty
    if not include_file_types and not exclude_file_types:
        return True

    # Check include filter
    if include_file_types and not any(file_name.endswith(f".{ext}") for ext in include_file_types):
        return False  # Skip files not matching the include list

    # Check exclude filter
    if exclude_file_types and any(file_name.endswith(f".{ext}") for ext in exclude_file_types):
        return False  # Skip files matching the exclude list

    return True  # File passes the filter

# Function to list directory contents
def list_directory(url, username, password):
    try:
        headers = {"Depth": "1"}
        response = requests.request("PROPFIND", url, auth=HTTPBasicAuth(username, password), headers=headers)
        if response.status_code != 207:
            print(f"Failed to list directory: {url}, Status Code: {response.status_code}")
            return []

        from xml.etree import ElementTree as ET
        tree = ET.fromstring(response.text)
        namespaces = {'D': 'DAV:'}
        files = []
        for response in tree.findall("D:response", namespaces):
            href = response.find("D:href", namespaces).text
            file_name = href.split("/")[-1]
            if not href.endswith("/") and file_matches_filters(file_name):  # Exclude directories
                files.append(file_name)
        return files
    except Exception as e:
        print(f"Error listing directory: {e}")
        return []

# Function to download a file
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

# Function to upload a file
def upload_file(local_path, remote_path):
    try:
        url = f"{options['webdav_hostname']}{remote_path}"
        with open(local_path, 'rb') as f:
            response = requests.put(url, auth=HTTPBasicAuth(options['webdav_login'], options['webdav_password']), data=f)
        if response.status_code in [200, 201, 204]:
            print(f"Uploaded {local_path}")
        else:
            print(f"Failed to upload {local_path}: {response.status_code}")
    except Exception as e:
        print(f"Error uploading file {local_path}: {e}")

# Function to sync files (two-way implementation)
def sync_files():
    print(f"Starting sync in {sync_mode} mode...")
    remote_files = list_directory(f"{options['webdav_hostname']}{remote_dir}", options['webdav_login'], options['webdav_password'])
    local_files = [f for f in os.listdir(local_dir) if file_matches_filters(f)]

    if sync_mode == "remote-to-local":
        for file in remote_files:
            local_path = os.path.join(local_dir, file)
            if not os.path.exists(local_path):
                download_file(f"{remote_dir}{file}", local_path)

    elif sync_mode == "local-to-remote":
        for file in local_files:
            remote_path = f"{remote_dir}{file}"
            if file not in remote_files:
                upload_file(os.path.join(local_dir, file), remote_path)

    elif sync_mode == "two-way":
        # Download files missing in local
        for file in remote_files:
            local_path = os.path.join(local_dir, file)
            if not os.path.exists(local_path):
                download_file(f"{remote_dir}{file}", local_path)

        # Upload files missing in remote
        for file in local_files:
            remote_path = f"{remote_dir}{file}"
            if file not in remote_files:
                upload_file(os.path.join(local_dir, file), remote_path)

# Run sync task
def run_tasks():
    print(f"Running tasks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    sync_files()

# Schedule sync tasks
if run_mode == "scheduled":
    schedule.every().day.at(scheduled_time).do(run_tasks)
    print(f"Scheduled tasks to run daily at {scheduled_time}.")

# Main execution
if __name__ == "__main__":
    if run_mode == "manual":
        run_tasks()  # Run immediately for testing
    else:
        while True:
            schedule.run_pending()
            time.sleep(1)
