from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.parse import urlparse, parse_qs
from rich.progress import (
    Progress,
    BarColumn,
    DownloadColumn,
    TransferSpeedColumn,
    TimeRemainingColumn,
)
import logging as log


def _filename_from_url(url: str) -> Optional[str]:
    parsed = urlparse(url)

    # 1. Try query param
    qs = parse_qs(parsed.query)
    if "path" in qs and qs["path"]:
        return Path(qs["path"][0]).name

    # 2. Try URL path
    name = Path(parsed.path).name
    if name:
        return name

    return None


def download_to_dir(
    url: str,
    out_dir: str = "/tmp/asset",
    filename: str | None = None,
    chunk_size: int = 1024 * 1024,  # 1MB
) -> Path:
    """
    Download a URL using pure Python with a rich progress bar.

    Args:
        url: URL to download
        out_dir: Target directory
        filename: Optional output filename
        chunk_size: Download chunk size in bytes

    Returns:
        Path to the downloaded file
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = _filename_from_url(url)
        if filename is None:
            raise ValueError(
                "Unable to infer filename from URL. Please provide one custom name."
            )

    log.info(f"Getting rosbag {filename} from URL:\n {url}")

    file_path = out_path / filename

    if file_path.exists():
        log.warning(
            f"File {filename} in path {out_dir} already exists. Skipping download."
        )
        return file_path

    req = Request(url, headers={"User-Agent": "python-downloader"})
    with urlopen(req) as response:
        total = response.headers.get("Content-Length")
        total = int(total) if total is not None else None

        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task(
                f"Downloading {filename}",
                total=total,
            )

            with open(file_path, "wb") as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    progress.update(task, advance=len(chunk))

    return file_path
