"""Download and validate the speed-dating CSV for Compose startup."""

import csv
import io
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path


OUTPUT = Path(__file__).resolve().parents[1] / "data/speed-dating-experiment/Speed Dating Data.csv"
SOURCES = (
    ("zip", "https://www.kaggle.com/api/v1/datasets/download/annavictoria/speed-dating-experiment"),
    ("csv", "https://www.stat.columbia.edu/~gelman/arm/examples/speed.dating/Speed%20Dating%20Data.csv"),
)
REQUIRED = {"wave", "iid", "id", "gender", "pid", "partner", "dec", "like"}


def valid_csv(path: Path) -> bool:
    try:
        with path.open(encoding="cp1252", newline="") as stream:
            reader = csv.DictReader(stream)
            if not REQUIRED <= set(reader.fieldnames or ()):
                return False
            waves = {row["wave"].strip() for row in reader}
            return len(waves) == 21
    except (OSError, UnicodeError, csv.Error):
        return False


def download_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "stable-matching-explorer/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read(50_000_001)
    if len(payload) > 50_000_000:
        raise ValueError("Dataset download exceeds 50 MB")
    return payload


def main() -> None:
    output = Path(os.environ.get("DATASET_PATH", str(OUTPUT)))
    output.parent.mkdir(parents=True, exist_ok=True)
    if valid_csv(output):
        print(f"Dataset ready: {output}", flush=True)
        return
    errors = []
    for kind, url in SOURCES:
        try:
            payload = download_bytes(url)
            if kind == "zip":
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    matches = [name for name in archive.namelist()
                               if Path(name).name == "Speed Dating Data.csv"]
                    if not matches:
                        raise ValueError("CSV is missing from downloaded archive")
                    with archive.open(matches[0]) as stream:
                        csv_bytes = stream.read()
            else:
                csv_bytes = payload
            with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as stream:
                temp_path = Path(stream.name)
                stream.write(csv_bytes)
            try:
                if not valid_csv(temp_path):
                    raise ValueError("Downloaded file failed CSV validation")
                shutil.move(str(temp_path), str(output))
            finally:
                temp_path.unlink(missing_ok=True)
            print(f"Downloaded dataset: {output}", flush=True)
            return
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("Could not download the dataset. " + " | ".join(errors))


if __name__ == "__main__":
    main()
