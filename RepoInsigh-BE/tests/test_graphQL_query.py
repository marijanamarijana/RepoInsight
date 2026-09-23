from services.graphQL.query_for_graphQL_full_analysis import REPOSITORY_ANALYSIS_QUERY


def test_repository_analysis_query_is_defined():
    assert REPOSITORY_ANALYSIS_QUERY
    assert isinstance(REPOSITORY_ANALYSIS_QUERY, str)


def test_repository_analysis_query_has_repository_variables():
    assert "$owner: String!" in REPOSITORY_ANALYSIS_QUERY
    assert "$repo: String!" in REPOSITORY_ANALYSIS_QUERY


def test_repository_analysis_query_has_basic_repository_data():
    required_fields = [
        "name",
        "nameWithOwner",
        "description",
        "stargazerCount",
        "forkCount",
        "isArchived",
        "isFork",
        "createdAt",
        "pushedAt",
    ]

    for field in required_fields:
        assert field in REPOSITORY_ANALYSIS_QUERY


def test_repository_analysis_query_has_language_information():
    assert "primaryLanguage" in REPOSITORY_ANALYSIS_QUERY
    assert "languages(first: 20" in REPOSITORY_ANALYSIS_QUERY
    assert "orderBy: {field: SIZE, direction: DESC}" in REPOSITORY_ANALYSIS_QUERY


def test_repository_analysis_query_has_contributor_history():
    assert "defaultBranchRef" in REPOSITORY_ANALYSIS_QUERY
    assert "history(first: 100)" in REPOSITORY_ANALYSIS_QUERY
    assert "committedDate" in REPOSITORY_ANALYSIS_QUERY
    assert "author" in REPOSITORY_ANALYSIS_QUERY
    assert "avatarUrl" in REPOSITORY_ANALYSIS_QUERY
    assert "message" in REPOSITORY_ANALYSIS_QUERY


def test_repository_analysis_query_has_releases():
    assert "releases(" in REPOSITORY_ANALYSIS_QUERY
    assert "tagName" in REPOSITORY_ANALYSIS_QUERY
    assert "publishedAt" in REPOSITORY_ANALYSIS_QUERY
    assert "isPrerelease" in REPOSITORY_ANALYSIS_QUERY


def test_repository_analysis_query_has_open_and_closed_issues():
    assert "openIssues:" in REPOSITORY_ANALYSIS_QUERY
    assert "closedIssues:" in REPOSITORY_ANALYSIS_QUERY
    assert "states: OPEN" in REPOSITORY_ANALYSIS_QUERY
    assert "states: CLOSED" in REPOSITORY_ANALYSIS_QUERY
    assert "labels(first: 20)" in REPOSITORY_ANALYSIS_QUERY


def test_repository_analysis_query_has_pull_requests():
    assert "openPullRequests:" in REPOSITORY_ANALYSIS_QUERY
    assert "closedPullRequests:" in REPOSITORY_ANALYSIS_QUERY
    assert "mergedAt" in REPOSITORY_ANALYSIS_QUERY


def test_repository_analysis_query_has_closed_pr_comments():
    assert "comments(first: 1)" in REPOSITORY_ANALYSIS_QUERY
    assert "createdAt" in REPOSITORY_ANALYSIS_QUERY