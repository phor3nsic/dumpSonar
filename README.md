```bash
     _                       __                        
  __| |_   _ _ __ ___  _ __ / _\ ___  _ __   __ _ _ __ 
 / _` | | | | '_ ` _ \| '_ \\ \ / _ \| '_ \ / _` | '__|
| (_| | |_| | | | | | | |_) |\ \ (_) | | | | (_| | |   
 \__,_|\__,_|_| |_| |_| .__/\__/\___/|_| |_|\__,_|_|   
                      |_|                     

                                        by @ph0r3nsic
```

## Description
`dumpSonar` is a Python script designed to download all projects/artifacts from exposed **SonarQube** and **Sonatype Nexus** instances using their REST APIs.

It supports two modes:
- **`sonarqube`** — downloads all projects' source code from a SonarQube instance.
- **`nexus`** — downloads all repositories' artifacts from a Sonatype Nexus instance.

## Features
- 🎯 **Two modes** — SonarQube and Sonatype Nexus.
- 📊 **Progress bars** — live per-project/per-repository download progress.
- 🔐 **Checksum validation** — Nexus assets are verified against their `sha1`/`md5`/`sha256` checksums.
- ⏩ **Resume** — files already present and valid are skipped (no re-download).
- ♻️ **Connection reuse** — single persistent HTTP session.
- 🔓 **`--insecure`** — skip TLS verification for self-signed/internal targets.
- 🎨 **Colored output** + a final summary (downloaded / skipped / verified / mismatch / failed / total size).

## Requirements
- Python 3.x
- Requests library (`pip install requests`)

## Usage
```bash
python3 dumpSonar.py --mode <sonarqube|nexus> --url <API URL> --output <output_directory>
```

### Parameters:
- `--mode`: Target type. Either `sonarqube` (default) or `nexus`.
- `--url`: The base API URL of the target. Must end with a slash.
  - SonarQube: ends with `/api/`
  - Nexus: ends with `/service/rest/v1/`
- `--output`: The directory where files will be saved (default: `output`).
- `--timeout`: Request timeout in seconds (default: `30`).
- `--insecure`: Disable TLS certificate verification (useful for self-signed/internal hosts).

## Examples
```bash
# SonarQube
python3 dumpSonar.py --mode sonarqube --url https://target/api/ --output /tmp/dump

# Sonatype Nexus
python3 dumpSonar.py --mode nexus --url https://target/service/rest/v1/ --output /tmp/dump
```

## How it works

### SonarQube mode
The script interacts with the SonarQube Web API to retrieve the list of projects, lists each project's files, and downloads their raw source code into the output directory.

| Step | Endpoint |
|------|----------|
| List projects | `components/search_projects?ps=300` |
| List files | `components/tree?component=<project>` |
| Download file | `sources/raw?key=<file>` |

### Nexus mode
The script interacts with the Sonatype Nexus REST API to list all repositories, paginates through each repository's components (using `continuationToken`), and downloads every asset via its `downloadUrl`.

| Step | Endpoint |
|------|----------|
| List repositories | `repositories` |
| List components | `components?repository=<repo>` (paginated) |
| Download asset | each asset's `downloadUrl` |

### Notes
- Make sure the target instance is accessible and you point `--url` to the correct API base path for the chosen mode.
- Ensure you have the necessary authorization to retrieve data from the target.
- SonarQube sources are saved as text; Nexus artifacts are saved as binary files named after their repository path.
