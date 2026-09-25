from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, read_json, write_json


class TestSet(list[dict[str, Any]]):
    @property
    def samples(self) -> list[dict[str, Any]]:
        return list(self)


def build_test_set(df: pd.DataFrame, output_path: Path) -> TestSet:
    if len(df) < 6:
        raise ValueError("At least six documents are required to build the test set.")
    papers = df.sort_values("paper_id").reset_index(drop=True)
    samples: list[dict[str, Any]] = []

    def add(kind: str, question: str, answer: str, ids: list[str]) -> None:
        samples.append({"id": f"eval_{len(samples) + 1:03d}", "type": kind, "question_type": kind, "question": question, "ground_truth": answer, "ground_truth_doc_ids": ids})

    row = papers.iloc[0]
    add("summary", f"What is the summary of the paper '{row.title}'?", first_sentence(row.summary), [row.paper_id])
    row = papers.iloc[1]
    add("authors", f"Who authored the paper '{row.title}'?", row.authors_joined, [row.paper_id])
    row = papers.iloc[2]
    add("date", f"When was the paper '{row.title}' published?", row.published, [row.paper_id])
    row = papers.iloc[3]
    add("categories", f"What categories describe the paper '{row.title}'?", row.categories_joined, [row.paper_id])
    left, right = papers.iloc[4], papers.iloc[5]
    answer = f"{left.title}: {left.categories_joined}; {right.title}: {right.categories_joined}"
    add("multi_hop", f"Compare the categories of '{left.title}' and '{right.title}'.", answer, [left.paper_id, right.paper_id])
    write_json(output_path, samples)
    return TestSet(samples)


def load_or_create_test_set(df: pd.DataFrame, output_path: Path, refresh: bool = False) -> TestSet:
    if output_path.exists() and not refresh:
        payload = read_json(output_path)
        if isinstance(payload, list) and payload:
            return TestSet(payload)
    return build_test_set(df, output_path)
