from datetime import datetime
from dateutil.parser import parse
from enum import Enum, verify
from fastapi import FastAPI, status
from fastapi.responses import RedirectResponse
from functools import lru_cache
from pydantic import BaseModel
from pydantic_core import Url
from typing import List
from urllib.parse import scheme_chars, urlparse, urljoin

import requests
import time

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

@lru_cache()
def fetch_upstream_json_cached(url: str, ttl_hash=None):
    del ttl_hash
    return requests.get(url).json()

def get_ttl_hash(seconds=30):
    return round(time.time() / seconds)

def fetch_upstream_json(url: str):
    return fetch_upstream_json_cached(url=url,
                                      ttl_hash=get_ttl_hash())

@app.get("/")
def root0():
    return RedirectResponse(url="/macos/stable/latest",
                            status_code=status.HTTP_302_FOUND)

@app.get("/{platform}")
def root1(platform: PlatformName):
    return RedirectResponse(url=f"/{platform.value}/stable/latest",
                            status_code=status.HTTP_302_FOUND)

@app.get("/{platform}/{channel}")
def root2(platform: PlatformName,
          channel: ChannelName):
    return RedirectResponse(url=f"/{platform.value}/{channel.value}/latest",
                            status_code=status.HTTP_302_FOUND)

@app.get("/{platform}/{channel}/{version}")
async def releases(platform: PlatformName,
                    channel: ChannelName,
                    version: str) -> list[Release]:
    releases : List[Release] = []
    json = fetch_upstream_json(f"https://storage.googleapis.com/flutter_infra_release/releases/releases_{platform.value}.json")
    base_url = urlparse(json["base_url"] + '/')

    scm_hash_filter = None
    version_filter = None

    if version == "all":
        version_filter = None
        scm_hash_filter = None
    elif version == "latest":
        version_filter = None
        scm_hash_filter = json["current_release"][channel.value]
    else:
        version_filter = version
        scm_hash_filter = None

    for release in json["releases"]:
        if release["channel"] != channel.value:
            continue
        if version_filter != None and version_filter != release["version"]:
            continue
        if scm_hash_filter != None and scm_hash_filter != release["hash"]:
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

