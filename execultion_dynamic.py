import requests
import json
from datetime import datetime
import io
import os

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
project_id = os.getenv("PROJECT_ID")
env_name = os.getenv("ENV_NAME")

def get_token():
    token_url = "https://id.core.matillion.com/oauth/dpc/token"

    payload = (
        "grant_type=client_credentials"
        f"&client_id={client_id}"
        f"&client_secret={client_secret}"
        "&audience=https%3A%2F%2Fapi.matillion.com"
    )

    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    response = requests.post(token_url, headers=headers, data=payload)
    response.raise_for_status()
    access_token = response.json().get("access_token")
    print("Access Token:", access_token, "\n")

    if not access_token:
        raise Exception("Failed to retrieve access token.")
    return access_token

def publish_artifact(token):
    url = f"https://us1.api.matillion.com/dpc/v1/projects/{project_id}/artifacts"
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_content = f"Artifact published at {current_time}"
    version_name = f'v_{current_time}'

    file_bytes = io.BytesIO(file_content.encode('utf-8'))

    files = {
        'file': ('artifact.txt', file_bytes, 'text/plain')
    }

    headers = {
        'Authorization': f'Bearer {token}',
        'environmentName': env_name,
        'versionName': version_name
    }

    response = requests.post(url, headers=headers, files=files)
    print("\nArtifact Response:", response.status_code)
    print(response.text)

def execute_pipeline(token, pipeline_name):
    url = f"https://us1.api.matillion.com/dpc/v1/projects/{project_id}/pipeline-executions"

    payload = json.dumps({
        "pipelineName": pipeline_name,
        "environmentName": env_name,
    })

    headers = {
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, data=payload)
    print(f"\nExecuted pipeline: {pipeline_name}")
    print("Status Code:", response.status_code)
    print(response.text)

def get_changed_pipelines():
    pipelines = []
    try:
        with open("changed_pipelines.txt", "r") as f:
            for line in f:
                filename = os.path.basename(line.strip())
                pipeline_name = filename.replace(".orch.yaml", "").replace(".tran.yaml", "")
                if pipeline_name:
                    pipelines.append(pipeline_name)
    except Exception as e:
        print("Error reading changed_pipelines.txt:", e)
    return pipelines

def main():
    try:
        token = get_token()
        publish_artifact(token)

        changed_pipelines = get_changed_pipelines()
        if changed_pipelines:
            print("\nChanged Pipelines Detected:", changed_pipelines)
            for pipeline_name in changed_pipelines:
                execute_pipeline(token, pipeline_name)
        else:
            print("No pipeline changes detected.")

    except Exception as e:
        print(f"\nExecution failed: {e}")

if __name__ == "__main__":
    main()
