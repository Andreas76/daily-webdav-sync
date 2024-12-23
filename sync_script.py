import os
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import schedule
import time
import logging
from logging.handlers import RotatingFileHandler

# Configure logging with a rotating file handler
log_file = "sync_debug.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Log to the terminal
        RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)  # 5MB per file, keep 5 backups
    ]
)

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
if not local_dir:
    raise ValueError("The 'LOCAL_DIR' environment variable must be set.")
if not os.path.exists(local_dir):
    raise FileNotFoundError(f"Local directory '{local_dir}' does not exist. Please create it.")

# Sync mode and file type filtering
sync_mode = os.getenv("SYNC_MODE", "remote-to-local")
include_file_types = os.getenv("INCLUDE_FILE_TYPES", "").split(",")
exclude_file_types = os.getenv("EXCLUDE_FILE_TYPES", "").split(",")

# Scheduling
run_mode = os.getenv("RUN_MODE", "scheduled")
scheduled_time = os.getenv("SCHEDULED_TIME", "02:00")

# Test WebDAV connection
def test_webdav_connection():
    try:
        url = f"{options['webdav_hostname']}{remote_dir}"
        response = requests.request("PROPFIND", url, auth=HTTPBasicAuth(options['webdav_login'], options['webdav_password']))
        if response.status_code == 207:
            logging.info("WebDAV connection successful!")
        else:
            logging.error(f"WebDAV connection failed with status code {response.status_code}")
    except Exception as e:
        logging.error(f"Error testing WebDAV connection: {e}")

# File filter function
def file_matches_filters(file_name):
    if not include_file_types and not exclude_file_types:
        logging.debug(f"File {file_name} passes filters (no filters applied).")
        return True
    if include_file_types and not any(file_name.endswith(f".{ext}") for ext in include_file_types):
        logging.debug(f"File {file_name} excluded by include filter.")
        return False
    if exclude_file_types and any(file_name.endswith(f".{ext}") for ext in exclude_file_types):
        logging.debug(f"File {file_name} excluded by exclude filter.")
        return False
    logging.debug(f"File {file_name} passes filters.")
    return True

def list_directory(url, username, password):
    """List the contents of a remote WebDAV directory."""
    try:
        headers = {"Depth": "1"}
        timeout = (10, 60)  # Connection timeout: 10s, Read timeout: 60s
        response = requests.request(
            "PROPFIND",
            url,
            auth=HTTPBasicAuth(username, password),
            headers=headers,
            timeout=timeout
        )
        logging.debug(f"Raw PROPFIND response for {url}: {response.text[:500]}")  # Log the first 500 characters for debugging
        if response.status_code != 207:
            logging.error(f"Failed to list directory: {url}, Status Code: {response.status_code}")
            return []

        from xml.etree import ElementTree as ET
        tree = ET.fromstring(response.text)
        namespaces = {"D": "DAV:"}
        entries = []
        for response in tree.findall("D:response", namespaces):
            href = response.find("D:href", namespaces).text
            is_dir = response.find("D:propstat/D:prop/D:resourcetype/D:collection", namespaces) is not None
            file_name = requests.utils.unquote(href.rstrip("/").split("/")[-1])  # Decode URL-encoded names
            entries.append((file_name, is_dir))
        logging.info(f"Entries in remote directory {url}: {entries}")
        return entries
    except requests.exceptions.Timeout:
        logging.error(f"Timeout while accessing {url}")
        return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Error listing directory {url}: {e}")
        return []

def sync_remote_to_local(remote_path, local_path):
    entries = list_directory(f"{options['webdav_hostname']}{remote_path}", options["webdav_login"], options["webdav_password"])
    logging.info(f"Syncing remote directory {remote_path} to local directory {local_path}. Found entries: {entries}")

    for name, is_dir in entries:
        remote_entry_path = f"{remote_path}{name}/" if is_dir else f"{remote_path}{name}"
        local_entry_path = os.path.join(local_path, name)

        if is_dir:
            # Skip recursive syncing for invalid remote directories
            if not is_valid_remote_directory(remote_entry_path):
                logging.warning(f"Skipping invalid remote directory: {remote_entry_path}")
                continue

            if not os.path.exists(local_entry_path):
                os.makedirs(local_entry_path, exist_ok=True)
                logging.info(f"Created local directory: {local_entry_path}")

            logging.info(f"Recursively syncing directory: {remote_entry_path}")
            sync_remote_to_local(remote_entry_path, local_entry_path)
        else:
            if file_matches_filters(name):
                logging.info(f"Downloading file: {remote_entry_path} to {local_entry_path}")
                download_file(remote_entry_path, local_entry_path)

def is_valid_remote_directory(remote_path):
    """Check if the remote path is a valid directory."""
    try:
        url = f"{options['webdav_hostname']}{remote_path}"
        headers = {"Depth": "1"}
        response = requests.request("PROPFIND", url, auth=HTTPBasicAuth(options["webdav_login"], options["webdav_password"]), headers=headers)
        if response.status_code == 207:
            logging.debug(f"Valid remote directory: {remote_path}")
            return True
        else:
            logging.warning(f"Invalid remote directory: {remote_path}, Status Code: {response.status_code}")
            return False
    except Exception as e:
        logging.error(f"Error validating remote directory {remote_path}: {e}")
        return False

def download_file(remote_path, local_path):
    """Download a file from the remote WebDAV server."""
    try:
        logging.info(f"Attempting to download {remote_path} to {local_path}")
        url = f"{options['webdav_hostname']}{remote_path}"
        timeout = (10, 60)  # Connection timeout: 10s, Read timeout: 60s
        with requests.get(
            url,
            auth=HTTPBasicAuth(options['webdav_login'], options['webdav_password']),
            stream=True,
            timeout=timeout
        ) as response:
            if response.status_code == 200:
                with open(local_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logging.info(f"Downloaded {local_path}")
            else:
                logging.error(f"Failed to download {remote_path}: {response.status_code}")
                if os.path.exists(local_path):
                    os.remove(local_path)  # Clean up partial file
    except requests.exceptions.Timeout:
        logging.error(f"Timeout while downloading {remote_path}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading file {remote_path}: {e}")
        if os.path.exists(local_path):
            os.remove(local_path)  # Clean up partial file

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
    logging.info(f"Starting sync in {sync_mode} mode...")
    if sync_mode == "remote-to-local":
        logging.info(f"Syncing remote directory {remote_dir} to local directory {local_dir}")
        sync_remote_to_local(remote_dir, local_dir)
    elif sync_mode == "local-to-remote":
        logging.info(f"Syncing local directory {local_dir} to remote directory {remote_dir}")
        sync_local_to_remote(local_dir, remote_dir)
    elif sync_mode == "two-way":
        logging.info(f"Performing two-way sync between {remote_dir} and {local_dir}")
        sync_remote_to_local(remote_dir, local_dir)
        sync_local_to_remote(local_dir, remote_dir)
    else:
        logging.error(f"Invalid SYNC_MODE: {sync_mode}. Supported modes are 'remote-to-local', 'local-to-remote', and 'two-way'.")

# Run tasks
def run_tasks():
    logging.info(f"Running tasks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...")
    sync_files()

# Schedule tasks
if run_mode == "scheduled":
    schedule.every().day.at(scheduled_time).do(run_tasks)
    logging.info(f"Scheduled tasks to run daily at {scheduled_time}.")

# Main execution
if __name__ == "__main__":
    try:
        if run_mode == "manual":
            run_tasks()
        elif run_mode == "scheduled":
            while True:
                schedule.run_pending()
                time.sleep(1)
        else:
            logging.error(f"Invalid RUN_MODE: {run_mode}. Supported modes are 'manual' and 'scheduled'.")
    except KeyboardInterrupt:
        logging.info("Script interrupted. Exiting gracefully.")
