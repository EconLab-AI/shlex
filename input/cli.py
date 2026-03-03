from __future__ import annotations

import asyncio
import sys


async def cli_main():
    """CLI entry point for local task submission."""
    if len(sys.argv) < 2:
        print("Usage: python -m input.cli 'Your task description'")
        print("       python -m input.cli --status")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--status":
        from core.database import Database
        db = Database("data/loop.db")
        await db.init()
        tasks = await db.list_tasks()
        if not tasks:
            print("No tasks.")
        for t in tasks:
            print(f"  [{t.status.value:8}] {t.title}")
        await db.close()
        return

    # Submit task via orchestrator
    print(f"Submitting task: {arg}")
    # For CLI usage, we just print what would happen
    print(f"Would create TASK_NEW event with raw_input='{arg}'")
    print("Use 'python main.py' to run the full orchestrator.")


if __name__ == "__main__":
    asyncio.run(cli_main())
