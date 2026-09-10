from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class RepoOverview(BaseModel):
    full_name: str
    description: Optional[str]
    stars: int
    forks: int
    open_issues: int
    watchers: int
    default_branch: str
    primary_language: Optional[str]
    license: Optional[str]
    created_at: str
    last_pushed_at: str
    days_since_last_push: int
    is_archived: bool
    is_fork: bool
    topics: list[str]


class LanguageEntry(BaseModel):
    language: str
    bytes: int
    percentage: float


class LanguageBreakdown(BaseModel):
    total_bytes: int
    languages: list[LanguageEntry]


class ContributorEntry(BaseModel):
    login: str
    avatar_url: str
    contributions: int
    percentage: float


class ContributorAnalysis(BaseModel):
    total_contributors_fetched: int
    total_commits_sampled: int
    bus_factor: int
    gini_coefficient: float
    top_contributors: list[ContributorEntry]
    ownership: dict[str, int]


class WeeklyActivity(BaseModel):
    week_start: str
    total: int
    days: list[int]


class CommitActivityAnalysis(BaseModel):
    sparkline: str
    peak_week_commits: int
    avg_commits_per_week: float
    weeks: list[WeeklyActivity]
    commits_by_day: dict[str, int]


class CommitHourBucket(BaseModel):
    hour: int
    count: int


class RecentCommitsAnalysis(BaseModel):
    total_sampled: int
    avg_message_length: float
    min_message_length: int
    max_message_length: int
    commits_by_hour: list[CommitHourBucket]
    peak_hour_utc: int


class LabelEntry(BaseModel):
    name: str
    count: int


class IssuesAnalysis(BaseModel):
    open_count: int
    closed_sampled: int
    open_sampled: int
    avg_close_time_days: Optional[float]
    median_close_time_days: Optional[float]
    stale_issues_count: int
    stale_threshold_days: int
    top_labels: list[LabelEntry]


class PullRequestsAnalysis(BaseModel):
    open_count: int
    closed_sampled: int
    merged_count: int
    rejected_count: int
    merge_rate_pct: float
    avg_time_to_merge_days: Optional[float]
    median_time_to_merge_days: Optional[float]
    avg_first_response_hours: Optional[float]


class ReleaseEntry(BaseModel):
    tag: str
    name: Optional[str]
    published_at: str
    is_prerelease: bool


class ReleasesAnalysis(BaseModel):
    total_fetched: int
    last_releases: list[ReleaseEntry]
    avg_days_between_releases: Optional[float]
    fastest_gap_days: Optional[int]
    slowest_gap_days: Optional[int]


class CodeFrequencyWeek(BaseModel):
    week_start: str
    additions: int
    deletions: int


class CodeFrequencyAnalysis(BaseModel):
    total_additions: int
    total_deletions: int
    net_lines: int
    recent_weeks: list[CodeFrequencyWeek]


class RepoSummary(BaseModel):
    repo: str
    stars: int
    forks: int
    open_issues: int
    days_since_last_push: int
    primary_language: Optional[str]
    bus_factor: int
    gini_coefficient: float
    pr_merge_rate_pct: float
    avg_pr_merge_days: Optional[float]
    avg_issue_close_days: Optional[float]
    total_releases: int
    top_contributors: list[str]


class FullAnalysis(BaseModel):
    overview: RepoOverview
    languages: LanguageBreakdown
    contributors: ContributorAnalysis
    commit_activity: CommitActivityAnalysis
    recent_commits: RecentCommitsAnalysis
    issues: IssuesAnalysis
    pull_requests: PullRequestsAnalysis
    releases: ReleasesAnalysis
    code_frequency: CodeFrequencyAnalysis
    summary: RepoSummary


class RateLimitStatus(BaseModel):
    limit: int
    remaining: int
    used: int
    reset_at: str
