import requests
import time
import os
import re
from datetime import datetime, timedelta

# Configuration
GITHUB_TOKEN = os.getenv("QUBIKA_GH_TOKEN")
REPO_OWNER = "manuelqubika"
REPO_NAME = "test-github-actions"
REVIEWER_EMAIL = os.getenv("REVIEWER_EMAIL")
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")     # Default base branch to merge into

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Pattern for cherry-pick PRs
CHERRY_PICK_PATTERN = re.compile(r'^SWSWV-\d+:.*Cherry-Pick', re.IGNORECASE)

def get_open_pull_requests():
    """Get all open PRs sorted by PR number (ascending)"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls?state=open&sort=created&direction=asc"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    prs = response.json()
    return sorted(prs, key=lambda x: x["number"])

def get_pr_details(pr_number):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_check_runs(pr_number):
    """Get all check runs for a PR"""
    pr_details = get_pr_details(pr_number)
    head_sha = pr_details["head"]["sha"]
    
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{head_sha}/check-runs"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("check_runs", [])

def enable_auto_merge(pr_number, merge_method="squash"):
    """Enable auto-merge for the PR"""
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/merge"
    data = {
        "merge_method": merge_method,
        "auto_merge": True
    }
    response = requests.put(url, headers=HEADERS, json=data)
    return response

def wait_for_checks_to_complete(pr_number, max_wait_minutes=30):
    """Wait for checks to complete with timeout"""
    start_time = datetime.now()
    last_status = ""
    
    while datetime.now() - start_time < timedelta(minutes=max_wait_minutes):
        check_runs = get_check_runs(pr_number)
        running_checks = [c for c in check_runs if c["status"] != "completed"]
        failed_checks = [c for c in check_runs if c["conclusion"] == "failure"]
        
        if failed_checks:
            return False, failed_checks
        
        if not running_checks:
            return True, []
        
        # Only print status if it changed
        current_status = f"Waiting for {len(running_checks)} checks: " + ", ".join([c["name"] for c in running_checks])
        if current_status != last_status:
            print(current_status)
            last_status = current_status
        
        time.sleep(30)
    
    return False, []

def is_mergeable(pr_number):
    """Check if PR is mergeable with retries"""
    max_retries = 3
    retry_delay = 2  # seconds
    
    for _ in range(max_retries):
        pr_data = get_pr_details(pr_number)
        
        if pr_data.get("mergeable") is not None:
            return pr_data["mergeable"] and pr_data["mergeable_state"] == "clean"
        
        time.sleep(retry_delay)
    
    return False

def add_reviewer(pr_number, reviewer_email):
    """Add reviewer to PR by email"""
    # First find the GitHub username from email
    search_url = f"https://api.github.com/search/users?q={reviewer_email}+in:email"
    response = requests.get(search_url, headers=HEADERS)
    
    if response.status_code != 200 or not response.json().get("items"):
        print(f"Could not find GitHub user with email {reviewer_email}")
        return False
    
    github_username = response.json()["items"][0]["login"]
    
    # Add the reviewer
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/requested_reviewers"
    data = {
        "reviewers": [github_username]
    }
    response = requests.post(url, headers=HEADERS, json=data)
    
    if response.status_code == 201:
        print(f"Added reviewer {github_username} to PR #{pr_number}")
        return True
    else:
        print(f"Failed to add reviewer. Status code: {response.status_code}")
        return False

def is_cherry_pick_pr(pr_title):
    """Check if PR title matches the cherry-pick pattern"""
    return bool(CHERRY_PICK_PATTERN.match(pr_title))

def process_pr(pr):
    """Process a single PR"""
    pr_number = pr["number"]
    pr_title = pr["title"]
    base_branch = pr["base"]["ref"]
    
    print(f"\nProcessing PR #{pr_number}: {pr_title} (target: {base_branch})")
    
    # Check if PR is targeting main and has cherry-pick in title
    if base_branch != BASE_BRANCH or not is_cherry_pick_pr(pr_title):
        print(f"Skipping PR #{pr_number} - doesn't match criteria")
        return False
    
    # Check mergeability
    if not is_mergeable(pr_number):
        print("PR is not immediately mergeable, checking for running checks...")
        checks_completed, failed_checks = wait_for_checks_to_complete(pr_number)
        
        if failed_checks:
            print(f"PR #{pr_number} has failed checks:")
            for check in failed_checks:
                print(f"- {check['name']}: {check.get('output', {}).get('title', 'No details')}")
            
            if REVIEWER_EMAIL:
                print(f"Adding reviewer due to failed checks")
                add_reviewer(pr_number, REVIEWER_EMAIL)
            return False
        
        if not checks_completed:
            print("Checks didn't complete in time")
            if REVIEWER_EMAIL:
                print(f"Adding reviewer due to timeout")
                add_reviewer(pr_number, REVIEWER_EMAIL)
            return False
        
        # Re-check mergeability after checks complete
        if not is_mergeable(pr_number):
            print("PR is still not mergeable after checks completed")
            if REVIEWER_EMAIL:
                print(f"Adding reviewer due to mergeability issues")
                add_reviewer(pr_number, REVIEWER_EMAIL)
            return False
    
    # Enable auto-merge
    print("PR is mergeable, enabling auto-merge...")
    response = enable_auto_merge(pr_number)
    
    if response.status_code == 200:
        print(f"Successfully enabled auto-merge for PR #{pr_number}")
        return True
    else:
        print(f"Failed to enable auto-merge. Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

def main():
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable not set")
        return
    
    try:
        pull_requests = get_open_pull_requests()
        print(f"Found {len(pull_requests)} open pull requests")
        
        for pr in pull_requests:
            process_pr(pr)
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()