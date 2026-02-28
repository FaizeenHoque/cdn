import hashlib
import json
import time

def hash(filepath):
    """Hash the file name - SHA256."""
    return hashlib.sha256(filepath.encode()).hexdigest()

def logToJson(filepath, hashValue):
    """Log original file name, Hash value (SHA256), and timestamp to a JSON file.. rehash file name if duplicate hash value is found."""

    log_entry = {
        "original_file_name": filepath,
        "hash_value": hashValue,
        "timestamp": time.time()
    }

    try:
        with open('cdn_log.json', 'r') as log_file:
            log_data = json.load(log_file)
    except FileNotFoundError:
        log_data = []

    # Check for duplicate hash value
    if any(entry['hash_value'] == hashValue for entry in log_data):
        print("Duplicate hash value found. Rehashing file name.")
        hashValue = hash(filepath + str(time.time()))
        log_entry['hash_value'] = hashValue

    log_data.append(log_entry)

    with open('cdn_log.json', 'w') as log_file:
        json.dump(log_data, log_file, indent=4)

def transferToCDN(filepath, hashValue, removefromstorage=False):
    import os
    import json
    import requests
    import base64

    # Get file extension
    file_ext = filepath.split('.')[-1]
    filename = f"{hashValue}.{file_ext}"

    # Load GitHub token from config file
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    with open(config_path, 'r') as config_file:
        config = json.load(config_file)
    github_token = config.get('github_token')
    if not github_token:
        raise Exception("GitHub token not found in config.json")

    # Read file content
    with open(filepath, 'rb') as f:
        content = f.read()

    # Prepare GitHub API request
    repo = "FaizeenHoque/cdn"
    branch = "main"
    github_api_url = f"https://api.github.com/repos/{repo}/contents/{filename}"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Check if file exists in repo
    file_resp = requests.get(github_api_url, headers=headers)
    if file_resp.status_code == 200:
        file_sha = file_resp.json()['sha']
    else:
        file_sha = None

    # Prepare payload
    payload = {
        "message": f"Add {filename} via transferToCDN",
        "content": base64.b64encode(content).decode('utf-8'),
        "branch": branch
    }
    if file_sha:
        payload["sha"] = file_sha

    # Upload file
    resp = requests.put(github_api_url, headers=headers, json=payload)
    if resp.status_code not in [200, 201]:
        raise Exception(f"Failed to upload file: {resp.text}")

    # Construct CDN URL
    cdn_url = f"https://cdn.faizeenhoque.dev/{filename}"

    # Remove file from storage if requested
    if removefromstorage:
        os.remove(filepath)

    return cdn_url


running = True

while running:
    userChoice = input("1. Transfer to CDN\n2. Show CDN Directory \n3. Exit\n")
    
    if userChoice == "1":
        filepath = input("Enter the file path: ")
        
        # Open the file and read its content
        try:
            with open(filepath, 'r') as file:
                content = file.read()
                print(content)

        except FileNotFoundError:
            print("File not found. Please try again.")
            break  
        except Exception as e:
            print(f"An error occurred: {e}")
            break  

        userConfirmation = input("Confirm CDN transfer? (yes/no): ").strip().lower()
        if userConfirmation == 'yes':
            print("CDN transfer initiated.")

            hashValue = hash(filepath)
            logToJson(filepath, hashValue)

            userConfirmation = input("Confirm file deletion from local storage? (yes/no): ").strip().lower()
            if userConfirmation == 'yes':
                transferToCDN(filepath, hashValue, removefromstorage=True)
            else:
                transferToCDN(filepath, hashValue, removefromstorage=False)

            print("CDN transfer completed.")
            running = False
        else:
            print("CDN transfer cancelled.")

    elif userChoice == "3":
        running = False