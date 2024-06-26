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
`dumpSonar` is a Python script designed to download all projects from SonarQube using its API.

## Requirements
- Python 3.x
- Requests library (`pip install requests`)

## Usage
```bash
python3 dumpSonar.py --url <SonarQube API URL> --output <output_directory>
```

### Parameters:
- `--url`: The base URL of your SonarQube instance, including `/api/`.
- `--output`: The directory where project files will be saved.

## Example
```bash
python3 dumpSonar.py --url https://sonarexample/api/ --output /tmp/projects
```

## How it works
The script interacts with the SonarQube API to retrieve a list of projects and downloads each project as a separate file into the specified output directory.

### Notes
- Make sure your SonarQube instance is accessible and the API endpoint (`/api/`) is correctly configured.
- Ensure you have necessary permissions and access to retrieve project data from SonarQube.