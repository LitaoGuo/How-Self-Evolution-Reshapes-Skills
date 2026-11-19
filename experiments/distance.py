"""Compute normalized TF-IDF cosine distances to ten topic-only drafts."""

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from .items import split_document

ROUNDS = (0, 1, 2, 3, 5, 7, 10, 15, 20, 25, 30)


def measure(run):
    files = [run / "original.md"] + [run / "chain" / f"{index:02d}.md" for index in ROUNDS[1:]]
    files += [run / "drafts" / f"{index:02d}.md" for index in range(1, 11)]
    texts = [split_document(file.read_text(encoding="utf-8"))[1] for file in files]
    vectorizer = TfidfVectorizer(
        lowercase=True, sublinear_tf=True, min_df=1,
        token_pattern=r"(?u)\b[\w\-./]{2,}\b",
    )
    vectors = vectorizer.fit_transform(texts)
    distances = 1 - (vectors @ vectors.T).toarray()
    drafts = distances[len(ROUNDS):, len(ROUNDS):]
    scale = drafts[np.triu_indices(10, 1)].mean()
    if scale <= 1e-12:
        raise ValueError(f"Drafts in {run} have zero pairwise distance.")
    return (distances[:len(ROUNDS), len(ROUNDS):].mean(axis=1) / scale).tolist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    originals = sorted(args.runs.glob("*/original.md"))
    if not originals:
        parser.error(f"No skills in {args.runs}")
    results = {original.parent.name: measure(original.parent) for original in originals}
    medians = np.median(list(results.values()), axis=0).tolist()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "rounds": ROUNDS, "median": medians, "per_skill": results,
    }, indent=2) + "\n", encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
