"""Download Stanford Dogs, Oxford-IIIT Pet and iNaturalist pet-bird photos, write manifest.csv.

Usage: python model/training/prepare_data.py [--data-dir DIR (default <repo>/data)] [--birds-per-species 400]
Output: DIR/manifest.csv with columns path,label,split (70/15/15 stratified, seed 42).
"""
import argparse
import csv
import random
import re
import tarfile
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from PIL import Image

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data"  # <repo>/data, git-ignored
STANFORD_URL = "http://vision.stanford.edu/aditya86/ImageNetDogs/images.tar"
OXFORD_URL = "https://thor.robots.ox.ac.uk/datasets/pets/images.tar.gz"
INAT_API = "https://api.inaturalist.org/v1"
UA = {"User-Agent": "whos-this-animal-student-project/0.1"}

# Oxford dog label -> Stanford label it duplicates. Oxford dogs not listed here stay as their own class.
OXFORD_TO_STANFORD = {
    "basset_hound": "basset", "beagle": "beagle", "boxer": "boxer", "chihuahua": "chihuahua",
    "english_setter": "english_setter", "german_shorthaired": "german_short_haired_pointer",
    "great_pyrenees": "great_pyrenees", "japanese_chin": "japanese_spaniel", "keeshond": "keeshond",
    "leonberger": "leonberg", "miniature_pinscher": "miniature_pinscher", "newfoundland": "newfoundland",
    "pomeranian": "pomeranian", "pug": "pug", "saint_bernard": "saint_bernard", "samoyed": "samoyed",
    "scottish_terrier": "scotch_terrier", "staffordshire_bull_terrier": "staffordshire_bullterrier",
    "wheaten_terrier": "soft_coated_wheaten_terrier", "yorkshire_terrier": "yorkshire_terrier",
}

# label -> iNaturalist scientific name (PRD §4)
BIRDS = {
    "budgerigar": "Melopsittacus undulatus",
    "cockatiel": "Nymphicus hollandicus",
    "rosy_faced_lovebird": "Agapornis roseicollis",
    "fischers_lovebird": "Agapornis fischeri",
    "domestic_canary": "Serinus canaria",
    "zebra_finch": "Taeniopygia guttata",
    "gouldian_finch": "Chloebia gouldiae",
    "society_finch": "Lonchura striata",
    "grey_parrot": "Psittacus erithacus",
    "monk_parakeet": "Myiopsitta monachus",
    "rose_ringed_parakeet": "Psittacula krameri",
    "sun_conure": "Aratinga solstitialis",
    "green_cheeked_conure": "Pyrrhura molinae",
    "blue_and_yellow_macaw": "Ara ararauna",
    "domestic_pigeon": "Columba livia",
}
# Pet forms of these look unlike the wild species (colour mutations), so take captive photos first.
CAPTIVE_FIRST = {"domestic_canary", "society_finch", "budgerigar"}


def norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def download(url: str, dest: Path) -> Path:
    if dest.exists():
        return dest
    print(f"downloading {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(20):  # flaky connections: resume from where the .part file stopped
        have = tmp.stat().st_size if tmp.exists() else 0
        try:
            with requests.get(url, stream=True, headers={**UA, "Range": f"bytes={have}-"}, timeout=60) as r:
                if r.status_code == 416:  # already complete
                    break
                r.raise_for_status()
                mode = "ab" if r.status_code == 206 else "wb"
                with open(tmp, mode) as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            break
        except requests.RequestException as e:
            print(f"  interrupted ({e}), retry {attempt + 1}")
            time.sleep(5)
    else:
        raise RuntimeError(f"download failed: {url}")
    tmp.rename(dest)
    return dest


def fetch_and_extract(url: str, archive: Path, into: Path) -> None:
    marker = into / ".extracted"
    if marker.exists():
        return
    download(url, archive)
    print(f"extracting {archive.name}")
    into.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as t:
        t.extractall(into, filter="data")
    marker.touch()


def stanford_dogs(data: Path) -> list[tuple[Path, str]]:
    fetch_and_extract(STANFORD_URL, data / "stanford_images.tar", data / "stanford")
    items = []
    for d in (data / "stanford" / "Images").iterdir():  # e.g. n02085620-Chihuahua
        label = "dog_" + norm(d.name.split("-", 1)[1])
        items += [(p, label) for p in d.glob("*.jpg")]
    return items


def oxford_pets(data: Path) -> list[tuple[Path, str]]:
    fetch_and_extract(OXFORD_URL, data / "oxford_images.tar.gz", data / "oxford")
    items = []
    for p in (data / "oxford" / "images").glob("*.jpg"):
        raw = p.stem.rsplit("_", 1)[0]
        if raw[0].isupper():  # Oxford convention: cat breeds are capitalised
            label = "cat_" + norm(raw)
        else:
            label = "dog_" + OXFORD_TO_STANFORD.get(norm(raw), norm(raw))
        items.append((p, label))
    return items


def inat_get(path: str, **params) -> dict:
    time.sleep(1.0)  # iNat asks for <= 1 req/s
    r = requests.get(f"{INAT_API}/{path}", params=params, headers=UA, timeout=60)
    r.raise_for_status()
    return r.json()


def inat_photo_urls(taxon_id: int, want: int, captive_first: bool) -> list[tuple[str, str, str]]:
    """(url, license, attribution) for up to `want` observations from verified wild and captive pools."""
    out, seen = [], set()
    pools = [{"quality_grade": "research"}, {"quality_grade": "casual", "captive": "true"}]
    if captive_first:
        pools.reverse()
    for extra in pools:
        id_below = None
        while len(out) < want:
            params = dict(taxon_id=taxon_id, photos="true", per_page=200, order_by="id", order="desc",
                          photo_license="cc0,cc-by,cc-by-nc", **extra)
            if id_below:
                params["id_below"] = id_below
            res = inat_get("observations", **params)["results"]
            if not res:
                break
            for obs in res:
                id_below = obs["id"]
                photo = obs["photos"][0]
                if photo["id"] in seen or not photo.get("license_code"):
                    continue
                seen.add(photo["id"])
                out.append((photo["url"].replace("square", "medium"), photo["license_code"], photo["attribution"]))
                if len(out) >= want:
                    break
    return out


def inat_birds(data: Path, per_species: int) -> list[tuple[Path, str]]:
    root = data / "birds"
    root.mkdir(parents=True, exist_ok=True)
    attribution = []
    items = []
    for label, sci in BIRDS.items():
        folder = root / label
        folder.mkdir(exist_ok=True)
        existing = list(folder.glob("*.jpg"))
        if len(existing) < per_species:
            taxa = inat_get("taxa", q=sci, rank="species")["results"]
            taxon_id = taxa[0]["id"]
            photos = inat_photo_urls(taxon_id, per_species, label in CAPTIVE_FIRST)
            print(f"{label}: {len(photos)} photos (taxon {taxon_id} {taxa[0]['name']})")

            def fetch(i_photo):
                i, (url, lic, attr) = i_photo
                dest = folder / f"{i:04d}.jpg"
                if not dest.exists():
                    try:
                        r = requests.get(url, headers=UA, timeout=60)
                        r.raise_for_status()
                        dest.write_bytes(r.content)
                    except requests.RequestException as e:
                        print(f"  skip {url}: {e}")
                        return None
                return (str(dest.relative_to(data)), lic, attr)

            with ThreadPoolExecutor(8) as pool:
                attribution += [a for a in pool.map(fetch, enumerate(photos)) if a]
        items += [(p, "bird_" + label) for p in folder.glob("*.jpg")]
    if attribution:
        with open(root / "attribution.csv", "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(attribution)
    return items


def readable(p: Path) -> bool:
    try:
        with Image.open(p) as im:
            im.verify()
        return True
    except Exception:
        return False


def split(items: list[tuple[Path, str]], seed: int = 42) -> list[tuple[Path, str, str]]:
    by_label = defaultdict(list)
    for p, label in items:
        by_label[label].append(p)
    rng = random.Random(seed)
    rows = []
    for label, paths in sorted(by_label.items()):
        paths.sort()
        rng.shuffle(paths)
        n_val = n_test = round(len(paths) * 0.15)
        for i, p in enumerate(paths):
            s = "test" if i < n_test else "val" if i < n_test + n_val else "train"
            rows.append((p, label, s))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    ap.add_argument("--birds-per-species", type=int, default=400)
    args = ap.parse_args()
    data = args.data_dir
    data.mkdir(parents=True, exist_ok=True)

    items = stanford_dogs(data) + oxford_pets(data) + inat_birds(data, args.birds_per_species)
    print(f"checking {len(items)} images")
    with ThreadPoolExecutor(8) as pool:
        ok = list(pool.map(lambda it: readable(it[0]), items))
    items = [it for it, good in zip(items, ok) if good]

    rows = split(items)
    with open(data / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "label", "split"])
        w.writerows((str(p.relative_to(data)), label, s) for p, label, s in rows)
    labels = sorted({r[1] for r in rows})
    print(f"{len(rows)} images, {len(labels)} classes -> {data / 'manifest.csv'}")


if __name__ == "__main__":
    main()
