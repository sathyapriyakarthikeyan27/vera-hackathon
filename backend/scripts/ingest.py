"""
Generic manual entrypoint for the RAG ingestion pipeline (all jurisdictions).

Run from the backend/ directory (needs DATABASE_URL + GEMINI_API_KEY in the env):

    python -m scripts.ingest                       # ingest every jurisdiction
    python -m scripts.ingest --jurisdiction India  # one jurisdiction (UK | India | ...)
    python -m scripts.ingest --force               # re-embed even if unchanged
    python -m scripts.ingest --review              # list facts awaiting human sign-off
    python -m scripts.ingest --verify <id> --by "Dr Smith"   # sign off one fact

This supersedes scripts/ingest_uk.py (kept for backwards compatibility). Initial
ingestion and fact sign-off are operator actions; the scheduled re-crawl is
tasks/ingestion.py.
"""

import argparse
import asyncio
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")


async def _run_ingest(jurisdiction: str, force: bool) -> None:
    from services.database import close_pool
    from services.ingestion.pipeline import ingest_registry
    from services.ingestion.registry import all_sources, sources_for

    if jurisdiction and jurisdiction.lower() != "all":
        sources = sources_for(jurisdiction)
        if not sources:
            print(f"Unknown jurisdiction '{jurisdiction}'. Nothing to do.")
            return
    else:
        sources = all_sources()

    try:
        results = await ingest_registry(sources, force=force)
    finally:
        await close_pool()

    print("\n=== Ingestion summary ===")
    for r in results:
        line = f"  {r['status']:>10}  {r['source_key']}"
        if r.get("chunks") is not None:
            line += f"  ({r['chunks']} chunks, {r.get('facts_staged', 0)} facts staged)"
        if r.get("error"):
            line += f"  ERROR: {r['error']}"
        print(line)
    print("\nStaged facts are UNVERIFIED. Review them: python -m scripts.ingest --review\n")


async def _run_review() -> None:
    from services.database import close_pool
    from services.rag_store import list_pending_facts

    try:
        facts = await list_pending_facts()
    finally:
        await close_pool()

    if not facts:
        print("No facts awaiting review.")
        return
    print(f"\n=== {len(facts)} fact(s) awaiting human sign-off ===")
    for f in facts:
        age = f"{f['eligible_age_min']}-{f['eligible_age_max']}"
        interval = f"{f['interval_months']}mo" if f["interval_months"] else "n/a"
        print(
            f"  [id {f['id']}] {f['jurisdiction']} · {f['programme']} · {f['cancer_type']} · "
            f"{f['sex']} · ages {age} · every {interval} · {f['cost']}\n"
            f"           method: {f['method']}\n"
            f"           source: {f['source_url']}"
        )
    print("\nSign off with: python -m scripts.ingest --verify <id> --by \"Your Name\"\n")


async def _run_verify(fact_id: int, by: str) -> None:
    from services.database import close_pool
    from services.rag_store import mark_fact_verified

    try:
        await mark_fact_verified(fact_id, by)
    finally:
        await close_pool()
    print(f"Fact {fact_id} verified by {by}. It is now eligible to surface to users.")


def main() -> None:
    p = argparse.ArgumentParser(description="VERA RAG ingestion (all jurisdictions)")
    p.add_argument("--jurisdiction", type=str, default="all", help="UK | India | ... | all")
    p.add_argument("--force", action="store_true", help="re-embed even if content is unchanged")
    p.add_argument("--review", action="store_true", help="list facts awaiting human sign-off")
    p.add_argument("--verify", type=int, metavar="FACT_ID", help="mark a staged fact as verified")
    p.add_argument("--by", type=str, default="", help="name of the reviewer (with --verify)")
    args = p.parse_args()

    if args.verify is not None:
        if not args.by:
            p.error("--verify requires --by \"Your Name\"")
        asyncio.run(_run_verify(args.verify, args.by))
    elif args.review:
        asyncio.run(_run_review())
    else:
        asyncio.run(_run_ingest(args.jurisdiction, args.force))


if __name__ == "__main__":
    main()
