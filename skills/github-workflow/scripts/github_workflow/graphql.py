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
