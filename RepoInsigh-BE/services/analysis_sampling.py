from __future__ import annotations

SAMPLE_PAGE_SIZE = 100

RECENT_COMMITS = 100
OPEN_ISSUES = 100
CLOSED_ISSUES = 100
OPEN_PULL_REQUESTS = 100
CLOSED_PULL_REQUESTS = 100
RELEASES = 20
CONTRIBUTORS = 100
REPOSITORY_TOPICS = 20
LANGUAGES = 20
ISSUE_LABELS = 20
CLOSED_PR_FIRST_COMMENT_SAMPLE = 10


def max_pages_for(limit: int, *, page_size: int = SAMPLE_PAGE_SIZE) -> int:
    if limit <= 0:
        return 0
    return (limit + page_size - 1) // page_size
