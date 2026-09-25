from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, read_json, write_json


class TestSet(list[dict[str, Any]]):
    @property
    def samples(self) -> list[dict[str, Any]]:
        return list(self)


def build_test_set(df: pd.DataFrame, output_path: Path | str) -> TestSet:
    """Build evaluation test set of 10 questions covering all 4 required question types:
    - summary (3 questions)
    - authors (3 questions)
    - date (2 questions)
    - categories (2 questions)
    """
    if len(df) < 10:
        raise ValueError("At least 10 documents are required to build the test set.")
    papers = df.sort_values("paper_id").reset_index(drop=True)
    samples: list[dict[str, Any]] = []

    def add(kind: str, question: str, answer: str, ids: list[str]) -> None:
        samples.append({
            "id": f"eval_{len(samples) + 1:03d}",
            "type": kind,
            "question_type": kind,
            "question": question,
            "ground_truth": str(answer).strip(),
            "ground_truth_doc_ids": ids,
        })

    # 3 Summary questions
    for i in (0, 1, 2):
        row = papers.iloc[i]
        add("summary", f"What is the summary of the paper '{row.title}'?", first_sentence(row.summary), [row.paper_id])

    # 3 Authors questions
    for i in (3, 4, 5):
        row = papers.iloc[i]
        add("authors", f"Who authored the paper '{row.title}'?", row.authors_joined, [row.paper_id])

    # 2 Date questions
    for i in (6, 7):
        row = papers.iloc[i]
        add("date", f"When was the paper '{row.title}' published?", str(row.published)[:10], [row.paper_id])

    # 2 Categories questions
    for i in (8, 9):
        row = papers.iloc[i]
        add("categories", f"What categories describe the paper '{row.title}'?", row.categories_joined, [row.paper_id])

    output_path = Path(output_path)
    write_json(output_path, samples)
    return TestSet(samples)


def load_or_create_test_set(df: pd.DataFrame, output_path: Path | str, refresh: bool = False) -> TestSet:
    output_path = Path(output_path)
    if output_path.exists() and not refresh:
        payload = read_json(output_path)
        if isinstance(payload, list) and payload:
            return TestSet(payload)
    return build_test_set(df, output_path)
