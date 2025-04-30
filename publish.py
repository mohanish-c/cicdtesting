import enum
import json
import os
import sys
from collections import namedtuple
from dataclasses import dataclass, field
import urllib.parse
import click
import requests
import logging
from datetime import datetime

client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
project_id = os.getenv("PROJECT_ID")
env_name = os.getenv("ENV_NAME")

def get_auth_token():
    url = "https://id.core.matillion.com/oauth/dpc/token"
    payload = (
        "grant_type=client_credentials"
        f"&client_id={client_id}"
        f"&client_secret={client_secret}"
        "&audience=https%3A%2F%2Fapi.matillion.com"
    )
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    response = requests.post(url, headers=headers, data=payload)
    response.raise_for_status()
    return response.json()["access_token"]

os.environ["API_BASE_URL"] = "https://us1.api.matillion.com/dpc/v1"
os.environ["AUTH_TOKEN"] = get_auth_token()

@dataclass
class PublicationFormEntry:
    key: str
    value: tuple


class PublicationResource:

    def id(self) -> str:
        raise NotImplementedError("id() must be implemented by subclasses.")

    def content(self) -> bytes | str:
        raise NotImplementedError("content() must be implemented by subclasses.")

    def content_type(self) -> str:
        return "text/plain"

    def headers(self) -> dict:
        return {}

    def form_data(self) -> PublicationFormEntry:
        return PublicationFormEntry(
            key=self.id(),
            value=(None, self.content(), self.content_type(), self.headers()),
        )


@dataclass
class FileResource(PublicationResource):
    name: str
    path: str
    type: str = field(default="text/plain")

    def id(self) -> str:
        return self.name

    def content(self) -> bytes:
        with open(self.path, "rb") as f:
            return f.read()

    def content_type(self) -> str:
        return self.type


ConnectorTypeData = namedtuple("ConnectorTypeData", ["id_key", "prefix"])


class ConnectorType(enum.Enum):
    FLEX = ConnectorTypeData("alternateId", "flex")
    CUSTOM = ConnectorTypeData("id", "custom")

    @property
    def id(self):
        return self.value.id_key

    @property
    def prefix(self):
        return self.value.prefix


@dataclass
class ConnectorResource(PublicationResource):
    type: ConnectorType
    connector: dict

    def id(self) -> str:
        if self.type.id not in self.connector:
            raise AttributeError(
                f"{self.type.prefix.title()} Connector does not have an {self.type.id} field."
            )

        return (
            f"connector-profile:{self.type.prefix}-{self.connector[self.type.id]}.json"
        )

    def content(self) -> bytes | str:
        return json.dumps(self.connector)

    def content_type(self) -> str:
        return "application/vnd.matillion.connector-profile+json"


if "API_BASE_URL" in os.environ and "AUTH_TOKEN" in os.environ:
    __API_BASE_URL = os.environ["API_BASE_URL"]
    __AUTH_TOKEN = os.environ["AUTH_TOKEN"]
    __CONNECTORS_URL = f"{__API_BASE_URL}/custom-connectors"
    __FLEX_CONNECTORS_URL = f"{__API_BASE_URL}/flex-connectors"

__IGNORED_DIRS = [".github" ".git", ".idea", ".vscode", "__pycache__", "venv", ".venv"]


@click.command
@click.option(
    "-p",
    "--path-to-project",
    help="""
              The path to a directory containing the Data Productivity Cloud project that you want to create an artifact from.

              When not specified, the current directory is used.
              """,
    type=str,
)
@click.option(
    "-l", "--log-level", help="The severity of the logger.", default="WARN", type=str
)
@click.option(
    "-V",
    "--version-name",
    help="Version name to be assigned to the artifact.",
    required=True,
    type=str,
)
@click.option(
    "-c", "--commit-hash", help="Commit hash of the artifact.", required=False, type=str
)
@click.option(
    "-P",
    "--project-id",
    help="The ID of the project to be published.",
    required=True,
    type=str,
)
@click.option(
    "-E",
    "--environment-name",
    help="The name of the environment to be published to.",
    required=True,
    type=str,
)
@click.option(
    "-b",
    "--branch-name",
    help="The name of the git branch the artifact was created from.",
    required=False,
    type=str,
)
@click.option(
    "-d",
    "--dry-run",
    help="Run without executing request to create artifact",
    is_flag=True,
)


def publish(
    path_to_project: [str],
    log_level: str,
    version_name: str,
    commit_hash: str,
    project_id: str,
    environment_name: str,
    dry_run: bool,
    branch_name: str,
):
    """
    A command line utility to create an Artifact via the Data Productivity Cloud public API.

    This artifact is built up from files on the file system and `custom-connector` Profiles which are dynamically retrieved from the Data Productivity Cloud API.

    The script will ignore the follow directories within your project [".github" ".git", ".idea", ".vscode", "__pycache__", "venv", ".venv"]

    Running this program requires the following environment variables to be set:

    - API_BASE_URL: The base URL of the Data Productivity Cloud public API. https://docs.matillion.com/data-productivity-cloud/api/docs/intro/#base-url

    - AUTH_TOKEN: The authentication token to be used. https://docs.matillion.com/data-productivity-cloud/api/docs/intro/#authentication
    """

    if "API_BASE_URL" not in os.environ:
        raise ValueError("Missing Environment Variable: API_BASE_URL.")

    if "AUTH_TOKEN" not in os.environ:
        raise ValueError("Missing Environment Variable: AUTH_TOKEN.")

    logger = logging.getLogger(__name__)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.getLevelName(log_level))
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    logger.setLevel(logging.getLevelName(log_level))

    if not path_to_project:
        path_to_project = "."

    environment_name = urllib.parse.quote_plus(environment_name)
    logger.debug("Publishing to: %s", __API_BASE_URL)
    logger.info("Publishing from project at path: %s", path_to_project)
    logger.info("Publishing Version Name: %s (%s)", version_name, commit_hash)
    logger.info("Publishing Project: %s", project_id)
    logger.info("Publishing Environment Name: %s", environment_name)
    logger.info("Publishing from Branch Name: %s", branch_name)

    headers = {
        "Authorization": f"Bearer {__AUTH_TOKEN}",
        "versionName": version_name,
        "commitHash": commit_hash,
        "environmentName": environment_name,
        "branch": branch_name,
    }

    resources_to_publish = []

    #     for p in path:
    logger.debug(f"Searching Path: {path_to_project}")
    for r in extract_pipeline_resources_from_path(path_to_project):
        logger.debug(
            f"Identified Resource ({type(r)}): Name:{r.id()} Path to file:{r.path}"
        )
        resources_to_publish.append(r)

    if not resources_to_publish:
        raise ValueError(
            f"No assets found in provided path: {path_to_project}. Exiting."
        )

    if dry_run:
        print("Dry run mode enabled. No request will be made to create artifact.")
        print(
            "The following assets would have been included in the artifact(excluding custom-connector profiles)."
        )
        for resource in resources_to_publish:
            print(f"Asset Name: {resource.id()}")
        return None

    else:
        for r in get_flex_connectors():
            logger.debug(f"Identified Connector ({type(r)}): {r.id()}")
            resources_to_publish.append(r)

        for r in get_custom_connectors():
            logger.debug(f"Identified Connector ({type(r)}): {r.id()}")
            resources_to_publish.append(r)

        file_data = {
            x.key: x.value for x in map(lambda x: x.form_data(), resources_to_publish)
        }

        resp = requests.post(
            f"{__API_BASE_URL}/projects/{project_id}/artifacts",
            headers=headers,
            files=file_data,
        )
        print(resp)
        if resp.status_code > 300 or resp.status_code < 200:
            raise Exception(f"Failed to publish: {resp.status_code}: {resp.content}")

        return resp.json()


def extract_pipeline_resources_from_path(path: str) -> [PublicationResource]:
    resources = []

    for root, dirs, files in os.walk(path, topdown=True):

        for d in __IGNORED_DIRS:
            if d in dirs:
                dirs.remove(d)

        for file in files:
            absolute_file_path = os.path.join(root, file)
            # Create the asset name relevate to the provided base path
            asset_name = os.path.relpath(absolute_file_path, path)
            # Get the actual path to the location of the asset
            path_to_asset = os.path.relpath(absolute_file_path)

            resource = FileResource(name=asset_name, path=path_to_asset)
            resources.append(resource)

    return resources


def get_flex_connectors() -> [PublicationResource]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {__AUTH_TOKEN}",
    }

    resp = requests.get(__FLEX_CONNECTORS_URL, headers=headers)
    print(resp)
    if resp.status_code != 200:
        raise Exception(
            f"Failed to retrieve flex connectors: {resp.status_code}: {resp}"
        )

    result = []

    for v in resp.json():
        result.append(ConnectorResource(type=ConnectorType.FLEX, connector=v))

    return result


def get_custom_connectors() -> [PublicationResource]:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {__AUTH_TOKEN}",
    }

    resp = requests.get(__CONNECTORS_URL, headers=headers)

    if resp.status_code != 200:
        raise Exception(
            f"Failed to retrieve custom connectors: {resp.status_code}: {resp}"
        )

    result = []

    for v in resp.json():
        result.append(ConnectorResource(type=ConnectorType.CUSTOM, connector=v))

    return result

if __name__ == "__main__":
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    version_name = f"v_{current_time}"

    sys.argv = [
        "publish",
        # "-p", "path/to/project",                          ## Path to project
        "-V", version_name,                                 ## Dynamic version name
        "-P", project_id,       ## Project ID
        "-E", env_name,                                    ## Environment name
        # "-c", "abc123",                                   ## Commit hash
        "-b", "main",                                       ## Branch name
        "-l", "DEBUG"                                       ## Log level
    ]
    publish()