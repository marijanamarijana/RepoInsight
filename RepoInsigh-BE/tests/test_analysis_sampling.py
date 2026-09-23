import re

from services import analysis_sampling as sampling
from services.graphQL.query_for_graphQL_full_analysis import REPOSITORY_ANALYSIS_QUERY


def test_max_pages_for_single_page_limits():
    assert sampling.max_pages_for(100) == 1
    assert sampling.max_pages_for(20) == 1
    assert sampling.max_pages_for(101) == 2


def test_graphql_query_first_limits_match_sampling_config():
    """GraphQL ``first: N`` values stay aligned with REST sample caps."""
    expectations = [
        (r"history\(first:\s*(\d+)\)", sampling.RECENT_COMMITS),
        (r"repositoryTopics\(first:\s*(\d+)\)", sampling.REPOSITORY_TOPICS),
        (r"languages\(first:\s*(\d+)", sampling.LANGUAGES),
        (r"releases\(\s*first:\s*(\d+)", sampling.RELEASES),
        (r"openIssues: issues\(\s*first:\s*(\d+)", sampling.OPEN_ISSUES),
        (r"closedIssues: issues\(\s*first:\s*(\d+)", sampling.CLOSED_ISSUES),
        (r"openPullRequests: pullRequests\(\s*first:\s*(\d+)", sampling.OPEN_PULL_REQUESTS),
        (r"closedPullRequests: pullRequests\(\s*first:\s*(\d+)", sampling.CLOSED_PULL_REQUESTS),
    ]

    for pattern, expected in expectations:
        match = re.search(pattern, REPOSITORY_ANALYSIS_QUERY)
        assert match is not None, f"pattern not found: {pattern}"
        assert int(match.group(1)) == expected
