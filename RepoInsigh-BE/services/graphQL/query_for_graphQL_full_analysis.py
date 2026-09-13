REPOSITORY_ANALYSIS_QUERY = """
query RepositoryAnalysis(
    $owner: String!
    $repo: String!
) {
    repository(owner: $owner, name: $repo) {

        name
        nameWithOwner
        description

        stargazerCount
        forkCount
        watchers {
            totalCount
        }

        issues {
            totalCount
        }

        isArchived
        isFork

        createdAt
        pushedAt

        primaryLanguage {
            name
        }

        licenseInfo {
            name
        }

        repositoryTopics(first: 20) {
            nodes {
                topic {
                    name
                }
            }
        }

        defaultBranchRef {
            name

            target {
                ... on Commit {
                    history(first: 100) {
                        nodes {
                            committedDate

                            author {
                                user {
                                    login
                                    avatarUrl
                                }
                            }

                            message
                        }
                    }
                }
            }
        }

        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) {
            edges {
                size
                node {
                    name
                }
            }
        }

        releases(
            first: 20
            orderBy: {field: CREATED_AT, direction: DESC}
        ) {
            nodes {
                tagName
                name
                publishedAt
                isPrerelease
            }
        }

        openIssues: issues(
            first: 100
            states: OPEN
            orderBy: {field: UPDATED_AT, direction: DESC}
        ) {
            nodes {
                number
                createdAt
                updatedAt

                labels(first: 20) {
                    nodes {
                        name
                    }
                }
            }
        }

        closedIssues: issues(
            first: 100
            states: CLOSED
            orderBy: {field: UPDATED_AT, direction: DESC}
        ) {
            nodes {
                number
                createdAt
                closedAt
                updatedAt

                labels(first: 20) {
                    nodes {
                        name
                    }
                }
            }
        }

        openPullRequests: pullRequests(
            first: 100
            states: OPEN
            orderBy: {field: UPDATED_AT, direction: DESC}
        ) {
            nodes {
                number
                createdAt
                updatedAt
                mergedAt
            }
        }

        closedPullRequests: pullRequests(
            first: 100
            states: CLOSED
            orderBy: {field: UPDATED_AT, direction: DESC}
        ) {
            nodes {
                number
                createdAt
                updatedAt
                mergedAt

                comments(first: 1) {
                    nodes {
                        createdAt
                    }
                }
            }
        }
    }
}
"""
