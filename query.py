#!/usr/bin/env python3
"""CLI to query meeting history.

Usage:
    python query.py all                        # list all meetings
    python query.py meeting <meeting_id>       # meetings by meeting ID
    python query.py thread <thread_id>         # meetings in a thread
    python query.py search <keyword>           # search summaries
    python query.py decisions <keyword>        # search decisions
    python query.py threads                    # list all threads
"""
import sys
from services.meeting_memory import MeetingMemory
from services.thread_store import get_all_threads


def print_meeting(m: dict, verbose: bool = False) -> None:
    date = m.get("date", "?")[:16]
    mid = m.get("meeting_id", "?")
    agenda = (m.get("agenda_raw", "") or "").replace("\n", " | ")[:60]
    decisions = m.get("decisions", [])
    summary = m.get("final_summary", "")[:100]
    thread = m.get("thread_id", "-")

    print(f"  [{date}] {mid}  thread={thread}")
    print(f"    Agenda   : {agenda}")
    if summary:
        print(f"    Summary  : {summary}...")
    if decisions:
        print(f"    Decisions: {'; '.join(str(d) for d in decisions[:3])}")
    if verbose:
        open_items = m.get("open_items", [])
        if open_items:
            print(f"    Open     : {'; '.join(str(o) for o in open_items[:3])}")
    print()


def cmd_all(mem: MeetingMemory) -> None:
    meetings = mem.get_all_meetings()
    print(f"\n  {len(meetings)} meetings in database:\n")
    for m in meetings:
        print_meeting(m)


def cmd_meeting(mem: MeetingMemory, meeting_id: str) -> None:
    meetings = mem.get_meeting_by_id(meeting_id)
    print(f"\n  {len(meetings)} meetings for {meeting_id}:\n")
    for m in meetings:
        print_meeting(m, verbose=True)


def cmd_thread(mem: MeetingMemory, thread_id: str) -> None:
    meetings = mem.get_meetings_by_thread(thread_id)
    print(f"\n  {len(meetings)} meetings in thread '{thread_id}':\n")
    for m in meetings:
        print_meeting(m, verbose=True)


def cmd_search(mem: MeetingMemory, keyword: str) -> None:
    meetings = mem.search_summaries(keyword)
    print(f"\n  {len(meetings)} meetings matching '{keyword}':\n")
    for m in meetings:
        print_meeting(m)


def cmd_decisions(mem: MeetingMemory, keyword: str) -> None:
    meetings = mem.search_decisions(keyword)
    print(f"\n  Decisions matching '{keyword}':\n")
    for m in meetings:
        date = m.get("date", "?")[:10]
        for d in m.get("decisions", []):
            if keyword.lower() in str(d).lower():
                print(f"    [{date}] {d}")
    print()


def cmd_threads() -> None:
    threads = get_all_threads()
    print(f"\n  {len(threads)} thread(s):\n")
    for t in threads:
        tid = t.get("thread_id", "?")
        count = t.get("meeting_count", 0)
        agenda = (t.get("agenda", "") or "").replace("\n", " | ")[:60]
        last = t.get("last_updated", "?")[:10]
        print(f"  [{tid}] {count} meetings, last: {last}")
        print(f"    Agenda: {agenda}")
        for m in t.get("meetings", []):
            print(f"      {m.get('date', '?')[:16]}  {m.get('title', '')}")
        print()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return

    mem = MeetingMemory()
    cmd = sys.argv[1]

    if cmd == "all":
        cmd_all(mem)
    elif cmd == "meeting" and len(sys.argv) >= 3:
        cmd_meeting(mem, sys.argv[2])
    elif cmd == "thread" and len(sys.argv) >= 3:
        cmd_thread(mem, sys.argv[2])
    elif cmd == "search" and len(sys.argv) >= 3:
        cmd_search(mem, " ".join(sys.argv[2:]))
    elif cmd == "decisions" and len(sys.argv) >= 3:
        cmd_decisions(mem, " ".join(sys.argv[2:]))
    elif cmd == "threads":
        cmd_threads()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
