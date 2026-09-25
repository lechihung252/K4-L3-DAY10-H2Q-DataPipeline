from __future__ import annotations

from typing import Any

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_dataframe, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import PaperRecord, fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from retrieval.index import LocalEmbeddingIndex

DEMO_QUESTIONS = [
    "Which papers in the corpus discuss agentic retrieval-augmented generation?",
    "Summarize the main idea of the most recent paper about RAG evaluation.",
]


def _log(step: str, message: str) -> None:
    print(f"[phase1] {step}: {message}")


def load_records(settings: Settings) -> tuple[list[PaperRecord], str]:
    """Live API khi REFRESH_SOURCE=1 hoac chua co snapshot; mac dinh doc snapshot offline."""
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        return fetch_source_records(settings), "live"
    return load_raw_records(settings.paths.raw_records_json), "offline-snapshot"


def load_or_build_test_set(df, settings: Settings) -> list[dict[str, Any]]:
    # Giu test set co dinh giua cac lan chay de metrics baseline/corrupted/repaired so sanh duoc.
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        return build_test_set(df, settings.paths.eval_testset)
    return read_json(settings.paths.eval_testset)


def run_agent_demo(settings: Settings, index: LocalEmbeddingIndex) -> list[dict[str, Any]]:
    try:
        agent = build_agent(settings, index)
        demo = [{"question": q, "answer": run_agent_question(agent, q)} for q in DEMO_QUESTIONS]
    except Exception as exc:  # LLM khong kha dung khong duoc lam hong baseline pipeline
        demo = [{"question": q, "error": f"Agent demo skipped: {type(exc).__name__}: {exc}"} for q in DEMO_QUESTIONS]
    write_json(settings.paths.demo_answers, demo)
    return demo


def main() -> None:
    settings = load_settings()
    run_date = now_utc()

    records, source_mode = load_records(settings)
    _log("ingestion", f"{len(records)} raw records ({source_mode})")

    clean_df = build_clean_dataframe(records, run_date)
    write_dataframe(clean_df, settings.paths.clean_csv, settings.paths.clean_json)
    _log("cleaning", f"{len(clean_df)} clean rows -> {settings.paths.clean_csv}")

    # Quality gate chay TRUOC khi index: data xau khong duoc vao vector store.
    quality = run_data_quality_checks(clean_df, settings, "baseline")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    _log("quality", f"success={quality['success']}, is_fresh={freshness['is_fresh']}")
    if not quality["success"]:
        raise RuntimeError(
            f"Quality gate failed, baseline index was not built. See {settings.paths.quality_dir}."
        )

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    _log("index", f"{len(index.documents)} documents -> Chroma collection '{index.collection_name}'")

    test_set = load_or_build_test_set(clean_df, settings)
    _log("testset", f"{len(test_set)} questions -> {settings.paths.eval_testset}")

    evaluation = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    metrics = evaluation.summary
    _log(
        "evaluation",
        f"hit_rate={metrics['retrieval_hit_rate']:.3f}, token_f1={metrics['mean_token_f1']:.3f}, "
        f"judge_accuracy={metrics['judge_accuracy']:.3f}",
    )

    source_summary = {
        "source_api": settings.source_api,
        "source_query": settings.source_query,
        "source_filter": settings.source_filter,
        "source_mode": source_mode,
        "run_date": run_date.isoformat(),
        "raw_records": len(records),
        "clean_rows": len(clean_df),
        "embedding_model": settings.embedding_model,
        "collection_name": index.collection_name,
        "top_k": settings.top_k,
        "llm_provider": settings.llm_provider,
    }
    generate_phase1_report(settings.paths.baseline_report, source_summary, metrics, quality, freshness)
    _log("report", f"{settings.paths.baseline_report}")

    demo = run_agent_demo(settings, index)
    _log("agent-demo", f"{sum('answer' in item for item in demo)}/{len(demo)} answered")
