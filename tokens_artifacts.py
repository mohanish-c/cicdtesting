import requests
import json
from datetime import datetime
import io
import os

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
## Function to get the bearer token
def get_token():
    token_url = "https://id.core.matillion.com/oauth/dpc/token"
    
    payload = (
        "grant_type=client_credentials"
        f"&client_id={client_id}"
        f"&client_secret={client_secret}"
        "&audience=https%3A%2F%2Fapi.matillion.com"
    )
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    response = requests.post(token_url, headers=headers, data=payload)
    response.raise_for_status()  # Raise an error for bad responses
    access_token = response.json().get("access_token")
    print("Access Token Response: ")
    print(access_token,"\n")  
   
    if not access_token:
        raise Exception("Failed to retrieve access token.")
    
    return access_token

## Function to Publish Artifacts
def get_artifacts(token):
    url = f"https://us1.api.matillion.com/dpc/v1/projects/94e19997-6afe-44de-82b2-880389d82996/artifacts"
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_content = f"Artifact published at {current_time}"
    version_name = f'v_{current_time}'

    # Create in-memory file
    file_bytes = io.BytesIO(file_content.encode('utf-8'))

    files = {
        'file': ('artifact.txt', file_bytes, 'text/plain')
    }

    headers = {
        'Authorization': f'Bearer {token}',
        'environmentName': 'env_prod',
        'branch': 'dev',
        'versionName':  version_name
    }

    response = requests.post(url, headers=headers, files=files)
    print("Artifacts Responses \n")
    print("Status Code:", response.status_code)
    print("Artifact Published Successfully")
    print("Version Name:", version_name)

## Main Function
def main():
    try:
        token = get_token()
        get_artifacts(token)
        print("Artifact Published with New Token and version name.")

    except Exception as e:
        print(f"HTTP Request failed: {e}")

if __name__ == "__main__":
    main()
