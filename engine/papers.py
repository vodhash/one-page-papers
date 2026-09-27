"""Where the papers live: papers/<category>/<slug>/, the category coming from the folder."""
import pathlib
from typing import NamedTuple

ROOT = pathlib.Path(__file__).resolve().parent.parent
# folder name: title in the README, in the order of the README
CATEGORIES = {
    "crypto": "Cryptocurrency",
    "computing": "Computing pioneers",
    "internet": "Internet & networking",
    "software": "Software practice",
    "manifestos": "Manifestos & announcements",
    "physics": "Physics & astronomy",
    "space": "Space exploration",
    "mathematics": "Mathematics",
    "life-sciences": "Biology & medicine",
    "data-viz": "Historical data visualization",
    "patents": "Patents",
    "history": "History & philosophy",
    "reference": "Reference sheets",
}
SHOWCASE = "bitcoin"  # the paper that the catalog of the README shows in every theme

class Paper(NamedTuple):
    category: str
    slug: str
    dir: pathlib.Path

def discover():
    """Every paper, sorted by category then slug. Raises ValueError on an unknown category
    or on a slug used twice, since slugs name the PDFs and the make targets."""
    papers, seen = [], {}
    for cat in sorted(p for p in (ROOT / "papers").iterdir() if p.is_dir()):
        if cat.name not in CATEGORIES:
            raise ValueError(f"papers/{cat.name}: unknown category (choose from {', '.join(CATEGORIES)})")
        for d in sorted(p for p in cat.iterdir() if (p / "meta.yaml").exists()):
            if d.name in CATEGORIES:
                raise ValueError(f"papers/{cat.name}/{d.name}: a slug cannot be the name of a category")
            if d.name in seen:
                raise ValueError(f"papers/{cat.name}/{d.name}: slug already used by papers/{seen[d.name]}/{d.name}")
            seen[d.name] = cat.name
            papers.append(Paper(cat.name, d.name, d))
    return papers
