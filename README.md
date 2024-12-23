# Daily WebDAV Sync

A lightweight, Dockerized tool for synchronizing directories using WebDAV. Supports one-way and two-way sync, daily scheduled runs, file type filtering, and manual execution.

---

## Features

- **Flexible Sync Options**:
  - `remote-to-local`, `local-to-remote`, or `two-way` synchronization.
- **Automated or Manual Execution**:
  - Schedule daily syncs or run tasks on demand.
- **File Type Filtering**:
  - Include or exclude specific file types during sync.
- **Lightweight & Secure**:
  - Runs in a Docker container using a non-root user for enhanced security.

---

## How It Works

### Sync Modes
- `remote-to-local`: Download files from a remote WebDAV directory to a local directory.
- `local-to-remote`: Upload files from a local directory to a remote WebDAV directory.
- `two-way`: Synchronize both directories to ensure consistency.

### File Filters
- `INCLUDE_FILE_TYPES`: Process only specified file types.
- `EXCLUDE_FILE_TYPES`: Skip specified file types.
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

### 1. Build the Docker Image:
   ```bash
   docker build -t daily-webdav-sync .
   ```

### 2. Run the Container:
Replace `<variables>` with your values:
```bash
sudo docker run -d \
    --name daily-webdav-sync \
    -e WEBDAV_HOSTNAME=https://your-webdav-server.com \
    -e WEBDAV_LOGIN=<your-login> \
    -e WEBDAV_PASSWORD=<your-password> \
    -e REMOTE_DIR=/path/to/remote/dir/ \
    -e LOCAL_DIR=/mnt/local-sync/ \
    -e SYNC_MODE=remote-to-local \
    -e RUN_MODE=scheduled \
    -e SCHEDULED_TIME=02:00 \
    -e TZ=Europe/Stockholm \
    -e INCLUDE_FILE_TYPES=mp4,srt,txt \
    -e EXCLUDE_FILE_TYPES=tmp,log \
    -v /your/local/directory:/mnt/local-sync \
    milligram/daily-webdav-sync:latest
```

### 3. Check Logs: View the container logs for sync updates:
docker logs daily-webdav-sync
