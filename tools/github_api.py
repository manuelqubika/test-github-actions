import os
import requests
import time

GITHUB_TOKEN = os.environ["QUBIKA_GH_TOKEN"]
OWNER = "manuelqubika"
REPO = "test-github-actions"
HEAD_BRANCH = "pr-1"
BASE_BRANCH = "main"
PR_TITLE = "Test Auto-Merge"
PR_BODY = "Description of what this PR does"
MERGE_METHOD = "SQUASH"

headers_rest = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}

headers_graphql = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json"
}

# Step 1: Create the Pull Request (REST API)
pr_response = requests.post(
    f"https://api.github.com/repos/{OWNER}/{REPO}/pulls",
    headers=headers_rest,
    json={
        "title": PR_TITLE,
        "head": HEAD_BRANCH,
        "base": BASE_BRANCH,
        "body": PR_BODY,
        "draft": False
    }
)
pr_response.raise_for_status()
pr = pr_response.json()
pr_number = pr["number"]
print(f"✅ Created PR #{pr_number}")

# 🔄 Wait to allow GitHub to process checks, branch protections, etc.
print("⏳ Waiting 30 seconds before enabling auto-merge...")
time.sleep(30)

# Step 2: Get Pull Request Node ID (GraphQL)
query_id = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      id
    }
  }
}
"""

resp_id = requests.post(
    "https://api.github.com/graphql",
    headers=headers_graphql,
    json={"query": query_id, "variables": {
        "owner": OWNER, "repo": REPO, "number": pr_number
    }}
)
resp_id.raise_for_status()
pr_id = resp_id.json()["data"]["repository"]["pullRequest"]["id"]
print(f"📦 PR node ID: {pr_id}")

# Step 3: Enable Auto-Merge (GraphQL)
enable_automerge = """
mutation($prId: ID!, $method: PullRequestMergeMethod!) {
  enablePullRequestAutoMerge(input: {
    pullRequestId: $prId,
    mergeMethod: $method
  }) {
    pullRequest {
      autoMergeRequest {
        enabledAt
      }
    }
  }
}
"""

resp_merge = requests.post(
    "https://api.github.com/graphql",
    headers=headers_graphql,
    json={"query": enable_automerge, "variables": {
        "prId": pr_id, "method": MERGE_METHOD
    }}
)
resp_merge.raise_for_status()

print("🚀 Auto-merge enabled (if all branch protection rules are met).")

