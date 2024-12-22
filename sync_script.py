import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import schedule
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Normalize path function
def normalize_path(path):
    return path.rstrip('/') + '/'

# Load WebDAV configuration from environment variables
options = {
    "webdav_hostname": os.getenv("WEBDAV_HOSTNAME"),
    "webdav_login": os.getenv("WEBDAV_LOGIN"),
    "webdav_password": os.getenv("WEBDAV_PASSWORD"),
}

# Validate WebDAV configuration
if not options["webdav_hostname"]:
    raise ValueError("The 'WEBDAV_HOSTNAME' environment variable must be set.")
if not options["webdav_login"]:
    raise ValueError("The 'WEBDAV_LOGIN' environment variable must be set.")
if not options["webdav_password"]:
    raise ValueError("The 'WEBDAV_PASSWORD' environment variable must be set.")

# Directories
remote_dir = normalize_path(os.getenv("REMOTE_DIR", ""))
if not remote_dir:
    raise ValueError("The 'REMOTE_DIR' environment variable must be set.")

local_dir = normalize_path(os.getenv("LOCAL_DIR"))
if not os.path.exists(local_dir):
    raise FileNotFoundError(f"Local directory '{local_dir}' does not exist. Please create it.")

# Sync mode and file type filtering
sync_mode = os.getenv("SYNC_MODE", "remote-to-local")
include_file_types = os.getenv("INCLUDE_FILE_TYPES", "").split(",")
exclude_file_types = os.getenv("EXCLUDE_FILE_TYPES", "").split(",")

# Scheduling
run_mode = os.getenv("RUN_MODE", "scheduled")
scheduled_time = os.getenv("SCHEDULED_TIME", "02:00")

# File filter function
def file_matches_filters(file_name):
    if not include_file_types and not exclude_file_types:
        return True
    if include_file_types and not any(file_name.endswith(f".{ext}") for ext in include_file_types):
        return False
    if exclude_file_types and any(file_name.endswith(f".{ext}") for ext in exclude_file_types):
        return False
    return True

# List directory function
def list_directory(url, username, password):
    try:
        headers = {"Depth": "1"}
        response = requests.request("PROPFIND", url, auth=HTTPBasicAuth(username, password), headers=headers)
        if response.status_code != 207:
            logging.error(f"Failed to list directory: {url}, Status Code: {response.status_code}")
            return []

        from xml.etree import ElementTree as ET
        tree = ET.fromstring(response.text)
        namespaces = {"D": "DAV:"}
        entries = []
        for response in tree.findall("D:response", namespaces):
            href = response.find("D:href", namespaces).text
            is_dir = response.find("D:resourcetype/D:collection", namespaces) is not None
            file_name = href.split("/")[-1]
            entries.append((file_name, is_dir))
        return entries
    except Exception as e:
        logging.error(f"Error listing directory: {e}")
        return []

# Recursive sync function
def sync_remote_to_local(remote_path, local_path):
    entries = list_directory(f"{options['webdav_hostname']}{remote_path}", options["webdav_login"], options["webdav_password"])
    for name, is_dir in entries:
        if is_dir:
            new_local_path = os.path.join(local_path, name)
            os.makedirs(new_local_path, exist_ok=True)
            sync_remote_to_local(f"{remote_path}{name}/", new_local_path)
        else:
            if file_matches_filters(name):
                local_file_path = os.path.join(local_path, name)
                download_file(f"{remote_path}{name}", local_file_path)

def sync_local_to_remote(local_path, remote_path):
    for root, dirs, files in os.walk(local_path):
        relative_path = os.path.relpath(root, local_path)
        remote_subdir = normalize_path(f"{remote_path}{relative_path}")
        for directory in dirs:
            remote_dir_path = f"{remote_subdir}{directory}/"
            create_remote_directory(remote_dir_path)
        for file in files:
            if file_matches_filters(file):
                remote_file_path = f"{remote_subdir}{file}"
                upload_file(os.path.join(root, file), remote_file_path)

# Download file function
def download_file(remote_path, local_path):
    try:
        url = f"{options['webdav_hostname']}{remote_path}"
        response = requests.get(url, auth=HTTPBasicAuth(options["webdav_login"], options["webdav_password"]), stream=True)
        if response.status_code == 200:
            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"Downloaded {local_path}")
        else:
            logging.error(f"Failed to download {remote_path}: {response.status_code}")
    except Exception as e:
        logging.error(f"Error downloading file {remote_path}: {e}")

# Upload file function
def upload_file(local_path, remote_path):
    try:
        url = f"{options['webdav_hostname']}{remote_path}"
        with open(local_path, "rb") as f:
            response = requests.put(url, auth=HTTPBasicAuth(options["webdav_login"], options["webdav_password"]), data=f)
        if response.status_code in [200, 201, 204]:
            logging.info(f"Uploaded {local_path}")
        else:
            logging.error(f"Failed to upload {local_path}: {response.status_code}")
    except Exception as e:
        logging.error(f"Error uploading file {local_path}: {e}")

# Create remote directory
def create_remote_directory(remote_path):
    try:
        url = f"{options['webdav_hostname']}{remote_path}"
        response = requests.request("MKCOL", url, auth=HTTPBasicAuth(options["webdav_login"], options["webdav_password"]))
        if response.status_code in [201, 204]:
            logging.info(f"Created remote directory {remote_path}")
        elif response.status_code == 405:
            logging.info(f"Remote directory {remote_path} already exists")
        else:
            logging.error(f"Failed to create remote directory {remote_path}: {response.status_code}")
    except Exception as e:
        logging.error(f"Error creating remote directory {remote_path}: {e}")

# Main sync logic
def sync_files():
    if sync_mode == "remote-to-local":
        sync_remote_to_local(remote_dir, local_dir)
    elif sync_mode == "local-to-remote":
        sync_local_to_remote(local_dir, remote_dir)
    elif sync_mode == "two-way":
        sync_remote_to_local(remote_dir, local_dir)
        sync_local_to_remote(local_dir, remote_dir)

# Schedule and run tasks
if run_mode == "scheduled":
    schedule.every().day.at(scheduled_time).do(sync_files)

if __name__ == "__main__":
    if run_mode == "manual":
        sync_files()
    elif run_mode == "scheduled":
        while True:
            schedule.run_pending()
            time.sleep(1)
