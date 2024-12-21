# Daily WebDAV Sync

A lightweight tool for synchronizing directories using WebDAV. Supports one-way and two-way sync, daily scheduled runs, file type filtering, and manual execution.

## Features

- **One-way or Two-way Sync**: Synchronize directories in one or both directions.
- **Daily Scheduling or Manual Runs**: Automate sync tasks or run them on demand.
- **File Type Filtering**: Include or exclude specific file types during sync.
- **Dockerized**: Runs in a lightweight Docker container for portability.

---

## How It Works

- **Sync Modes**:
  - `remote-to-local`: Downloads files from the remote directory to the local directory.
  - `local-to-remote`: Uploads files from the local directory to the remote directory.
  - `two-way`: Synchronizes both directories, ensuring they are identical.

- **File Filtering**:
  - `INCLUDE_FILE_TYPES`: Specify which file types to include during sync.
  - `EXCLUDE_FILE_TYPES`: Specify which file types to exclude.
  - If both are empty, all files are processed.

---

## Configuration

The tool is configured using environment variables:

| Variable            | Description                                                      | Example Value               |
|---------------------|------------------------------------------------------------------|-----------------------------|
| `WEBDAV_HOSTNAME`   | WebDAV server URL                                               | `https://example.com`        |
| `WEBDAV_LOGIN`      | WebDAV username                                                 | `your-username`              |
| `WEBDAV_PASSWORD`   | WebDAV password                                                 | `your-password`              |
| `REMOTE_DIR`        | Remote directory to sync                                        | `/remote/folder/`            |
| `LOCAL_DIR`         | Local directory for syncing                                     | `/path/to/local/dir`         |
| `SYNC_MODE`         | Sync mode: `remote-to-local`, `local-to-remote`, or `two-way`   | `two-way`                    |
| `SCHEDULED_TIME`    | Time for daily scheduled sync (24-hour format)                  | `02:00`                      |
| `RUN_MODE`          | `manual` for immediate sync or `scheduled` for daily sync       | `manual`                     |
| `INCLUDE_FILE_TYPES`| Comma-separated list of file extensions to include              | `mp4,srt`                    |
| `EXCLUDE_FILE_TYPES`| Comma-separated list of file extensions to exclude              | `tmp,log`                    |

---

## Usage

### Running with Docker

1. **Build the Docker Image**:
   ```bash
   docker build -t daily-webdav-sync .
