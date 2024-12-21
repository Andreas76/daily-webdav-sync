# Daily WebDAV Sync

A simple WebDAV sync tool for syncing single directories. Supports one-way or two-way synchronization with file filtering.

## Features
- One-way or two-way synchronization.
- File filtering by extensions (include or exclude specific types).
- Daily scheduled or manual sync options.
- Lightweight Docker container for portability.

## Usage

### Environment Variables
| Variable            | Description                                                      | Example Value                |
|---------------------|------------------------------------------------------------------|------------------------------|
| `WEBDAV_HOSTNAME`   | WebDAV server URL                                               | `https://example.com`        |
| `WEBDAV_LOGIN`      | WebDAV username                                                 | `your-username`              |
| `WEBDAV_PASSWORD`   | WebDAV password                                                 | `your-password`              |
| `REMOTE_DIR`        | Remote directory to sync                                        | `/remote/folder/`            |
| `LOCAL_DIR`         | Local directory for syncing                                     | `/path/to/local/dir`         |
| `SYNC_MODE`         | Sync mode: `one-way-remote-to-local`, `one-way-local-to-remote`, or `two-way` | `two-way`                   |
| `SCHEDULED_TIME`    | Time for daily scheduled sync (24-hour format)                  | `02:00`                      |
| `RUN_MODE`          | `manual` for immediate sync or `scheduled` for daily sync       | `manual`                     |
| `INCLUDE_FILE_TYPES`| Comma-separated list of file extensions to include              | `mp4,srt`                    |
| `EXCLUDE_FILE_TYPES`| Comma-separated list of file extensions to exclude              | `tmp,log`                    |

### Running with Docker
1. Build the Docker image:
   ```bash
   docker build -t daily-webdav-sync .
