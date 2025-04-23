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

import requests
import time
import os
import re
from datetime import datetime, timedelta

# Configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # From environment variable
REVIEWER_EMAILS = os.getenv("REVIEWER_EMAILS", "").split(",")  # Comma-separated emails
REPO_OWNER = os.getenv("REPO_OWNER", "owner_name")  # With default
REPO_NAME = os.getenv("REPO_NAME", "repo_name")    # With default
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")     # Default base branch to merge into

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Pattern for cherry-pick PRs
CHERRY_PICK_PATTERN = re.compile(r'^SWSWV-\d+:.*Cherry-Pick', re.IGNORECASE)

def get_github_usernames(emails):
    """Convert email addresses to GitHub usernames"""
    usernames = []
    for email in emails:
        email = email.strip()
        if not email:
            continue
            
        search_url = f"https://api.github.com/search/users?q={email}+in:email"
        response = requests.get(search_url, headers=HEADERS)
        
        if response.status_code == 200 and response.json().get("items"):
            usernames.append(response.json()["items"][0]["login"])
        else:
            print(f"Could not find GitHub user with email {email}")
    
    return usernames

def add_reviewers(pr_number, reviewer_emails):
    """Add multiple reviewers to PR by email"""
    if not reviewer_emails:
        print("No reviewer emails provided")
        return False
    
    # Convert emails to GitHub usernames
    reviewers = get_github_usernames(reviewer_emails)
    if not reviewers:
        print("No valid reviewers found")
        return False
    
    # Add the reviewers
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/requested_reviewers"
    data = {
        "reviewers": reviewers
    }
    response = requests.post(url, headers=HEADERS, json=data)
    
    if response.status_code == 201:
        print(f"Added reviewers {', '.join(reviewers)} to PR #{pr_number}")
        return True
    else:
        print(f"Failed to add reviewers. Status code: {response.status_code}")
        return False

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
            
            if REVIEWER_EMAILS:
                print(f"Adding reviewers due to failed checks")
                add_reviewers(pr_number, REVIEWER_EMAILS)
            return False
        
        if not checks_completed:
            print("Checks didn't complete in time")
            if REVIEWER_EMAILS:
                print(f"Adding reviewers due to timeout")
                add_reviewers(pr_number, REVIEWER_EMAILS)
            return False
        
        # Re-check mergeability after checks complete
        if not is_mergeable(pr_number):
            print("PR is still not mergeable after checks completed")
            if REVIEWER_EMAILS:
                print(f"Adding reviewers due to mergeability issues")
                add_reviewers(pr_number, REVIEWER_EMAILS)
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
        
        # Filter and clean reviewer emails
        reviewer_emails = [email.strip() for email in REVIEWER_EMAILS if email.strip()]
        if reviewer_emails:
            print(f"Configured reviewers: {', '.join(reviewer_emails)}")
        
        for pr in pull_requests:
            process_pr(pr)
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()