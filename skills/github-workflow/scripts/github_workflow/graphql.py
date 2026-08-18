"""Static GraphQL documents for GitHub Projects V2."""

PROJECT_LIST_USER = """
query UserProjectList($owner: String!, $first: Int!) {
  user(login: $owner) { projectsV2(first: $first) { nodes { id number title shortDescription url closed } } }
}
"""

PROJECT_LIST_ORGANIZATION = """
query OrganizationProjectList($owner: String!, $first: Int!) {
  organization(login: $owner) { projectsV2(first: $first) { nodes { id number title shortDescription url closed } } }
}
"""

PROJECT_ID_USER = """
query UserProjectId($owner: String!, $number: Int!) {
  user(login: $owner) { projectV2(number: $number) { id number title url } }
}
"""

PROJECT_ID_ORGANIZATION = """
query OrganizationProjectId($owner: String!, $number: Int!) {
  organization(login: $owner) { projectV2(number: $number) { id number title url } }
}
"""

ADD_PROJECT_ITEM = """
mutation AddProjectItem($project: ID!, $content: ID!) {
  addProjectV2ItemById(input: {projectId: $project, contentId: $content}) {
    item { id }
  }
}
"""

SET_PROJECT_FIELD = """
mutation SetProjectField($project: ID!, $item: ID!, $field: ID!, $value: ProjectV2FieldValue!) {
  updateProjectV2ItemFieldValue(
    input: {projectId: $project, itemId: $item, fieldId: $field, value: $value}
  ) { projectV2Item { id } }
}
"""

PROJECT_READ_USER = """
query UserProject($owner: String!, $number: Int!) {
  user(login: $owner) {
    projectV2(number: $number) {
      id number title shortDescription readme url public closed createdAt updatedAt
      items(first: 1) { totalCount }
      fields(first: 1) { totalCount }
      views(first: 1) { totalCount }
    }
  }
}
"""

PROJECT_READ_ORGANIZATION = PROJECT_READ_USER.replace(
    "query UserProject", "query OrganizationProject"
).replace("user(login: $owner)", "organization(login: $owner)")

PROJECT_FIELDS_USER = """
query UserProjectFields($owner: String!, $number: Int!, $first: Int!) {
  user(login: $owner) {
    projectV2(number: $number) {
      fields(first: $first) {
        totalCount
        nodes {
          __typename
          ... on ProjectV2Field { id name dataType }
          ... on ProjectV2SingleSelectField { id name dataType options { id name color description } }
          ... on ProjectV2IterationField {
            id name dataType
            configuration {
              iterations { id title startDate duration }
              completedIterations { id title startDate duration }
            }
          }
        }
      }
    }
  }
}
"""

PROJECT_FIELDS_ORGANIZATION = PROJECT_FIELDS_USER.replace(
    "query UserProjectFields", "query OrganizationProjectFields"
).replace("user(login: $owner)", "organization(login: $owner)")

PROJECT_VIEWS_USER = """
query UserProjectViews($owner: String!, $number: Int!, $first: Int!) {
  user(login: $owner) {
    projectV2(number: $number) {
      views(first: $first) { totalCount nodes { id number name layout filter } }
    }
  }
}
"""

PROJECT_VIEWS_ORGANIZATION = PROJECT_VIEWS_USER.replace(
    "query UserProjectViews", "query OrganizationProjectViews"
).replace("user(login: $owner)", "organization(login: $owner)")

PROJECT_ITEMS_USER = """
query UserProjectItems($owner: String!, $number: Int!, $first: Int!, $after: String, $query: String) {
  user(login: $owner) {
    projectV2(number: $number) {
      items(first: $first, after: $after, query: $query) {
        totalCount
        pageInfo { hasNextPage endCursor }
        nodes {
          id isArchived createdAt updatedAt
          content {
            __typename
            ... on Issue {
              id number title url state stateReason createdAt updatedAt closedAt
              repository { nameWithOwner }
              author { login }
            }
            ... on PullRequest {
              id number title url state isDraft mergedAt createdAt updatedAt closedAt
              repository { nameWithOwner }
              author { login }
            }
            ... on DraftIssue { id title body createdAt updatedAt }
          }
          fieldValues(first: 100) {
            nodes {
              __typename
              ... on ProjectV2ItemFieldTextValue { text field { ... on ProjectV2Field { id name } } }
              ... on ProjectV2ItemFieldNumberValue { number field { ... on ProjectV2Field { id name } } }
              ... on ProjectV2ItemFieldDateValue { date field { ... on ProjectV2Field { id name } } }
              ... on ProjectV2ItemFieldSingleSelectValue { name optionId field { ... on ProjectV2SingleSelectField { id name } } }
              ... on ProjectV2ItemFieldIterationValue { title iterationId startDate duration field { ... on ProjectV2IterationField { id name } } }
              ... on ProjectV2ItemFieldRepositoryValue { repository { nameWithOwner } field { ... on ProjectV2Field { id name } } }
              ... on ProjectV2ItemFieldLabelValue { labels(first: 20) { nodes { name } } field { ... on ProjectV2Field { id name } } }
              ... on ProjectV2ItemFieldMilestoneValue { milestone { title } field { ... on ProjectV2Field { id name } } }
              ... on ProjectV2ItemFieldUserValue { users(first: 20) { nodes { login } } field { ... on ProjectV2Field { id name } } }
            }
          }
        }
      }
    }
  }
}
"""

PROJECT_ITEMS_ORGANIZATION = PROJECT_ITEMS_USER.replace(
    "query UserProjectItems", "query OrganizationProjectItems"
).replace("user(login: $owner)", "organization(login: $owner)")

PR_REVIEW_STATE = """
query PullRequestReviewState($owner: String!, $repo: String!, $number: Int!, $first: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      reviewDecision mergeStateStatus
      reviewThreads(first: $first) {
        totalCount pageInfo { hasNextPage }
        nodes { isResolved isOutdated }
      }
    }
  }
}
"""
