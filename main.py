from datetime import datetime
from fastapi import FastAPI
from pydantic_core import Url
from enum import Enum
import requests
from pydantic import BaseModel
from typing import List
from dateutil.parser import parse
from urllib.parse import urlparse, urljoin

app = FastAPI()

class Release(BaseModel):
    scm_hash: str
    channel: str
    flutter_version: str
    dart_version: str
    host_arch: str
    release_date: datetime
    archive_url: Url
    archive_sha256: str

class PlatformName(str, Enum):
    macos = "macos"
    windows = "windows"
    linux = "linux"

class ChannelName(str, Enum):
    beta = "beta"
    dev = "dev"
    stable = "stable"

@app.get("/{platform}/{channel}")
async def root(platform: PlatformName, channel: ChannelName) -> list[Release]:
    releases : List[Release] = []
    json = requests.get(f"https://storage.googleapis.com/flutter_infra_release/releases/releases_{platform.value}.json").json()
    base_url = urlparse(json["base_url"])
    for release in json["releases"]:
        if release["channel"] != channel.value:
            continue
        release_record = Release(
            scm_hash=release["hash"],
            channel=release["channel"],
            flutter_version=release["version"],
            dart_version=release.get("dart_sdk_version", "unknown"),
            host_arch=release.get("dart_sdk_arch", "unknown"),
            release_date=parse(release["release_date"]),
            archive_url=urljoin(base_url.geturl(), release["archive"]),
            archive_sha256=release["sha256"],
        )
        releases.append(release_record)
    return releases

