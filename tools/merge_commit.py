import requests
import time
import os
import argparse
from datetime import datetime, timedelta



# Configuration
GITHUB_TOKEN = os.getenv("QUBIKA_GH_TOKEN")
REPO_OWNER = "manuelqubika"
REPO_NAME = "test-github-actions"
REVIEWER_EMAIL = os.getenv("REVIEWER_EMAIL")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_open_pull_requests():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls?state=open"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_pr_details(pr_number):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_running_checks(pr_number):
    # Get check runs for the PR
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{pr_number}/check-runs"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    
    running_checks = [check for check in data.get("check_runs", []) 
                     if check["status"] != "completed"]
    return running_checks

def wait_for_checks_to_complete(pr_number, max_wait_minutes=30):
    start_time = datetime.now()
    while datetime.now() - start_time < timedelta(minutes=max_wait_minutes):
        running_checks = get_running_checks(pr_number)
        if not running_checks:
            return True
        
        print(f"Waiting for {len(running_checks)} checks to complete...")
        print("Still running:", ", ".join([check["name"] for check in running_checks]))
        time.sleep(30)
    
    return False

def is_mergeable(pr_number):
    max_retries = 3
    retry_delay = 2  # seconds
    
    for _ in range(max_retries):
        pr_data = get_pr_details(pr_number)
        
        if pr_data.get("mergeable") is not None:
            return pr_data["mergeable"] and pr_data["mergeable_state"] == "clean"
        
        time.sleep(retry_delay)
    
    return False

def add_reviewer(pr_number, reviewer_email):
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

def merge_pull_request(pr_number, commit_title):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/merge"
    data = {
        "merge_method": "squash",
        "commit_title": commit_title,
    }
    response = requests.put(url, headers=HEADERS, json=data)
    return response

def handle_blocked_pr(pr_number, pr_title):
    print(f"PR #{pr_number} is blocked from merging")
    
    # First check if there are running checks
    running_checks = get_running_checks(pr_number)
    if running_checks:
        print(f"Waiting for {len(running_checks)} checks to complete...")
        if wait_for_checks_to_complete(pr_number):
            # Checks completed, check mergeability again
            if is_mergeable(pr_number):
                print("Checks completed, PR is now mergeable")
                return merge_pull_request(pr_number, pr_title)
    
    # If still not mergeable, add reviewer
    if REVIEWER_EMAIL:
        print(f"Adding reviewer {REVIEWER_EMAIL} to PR #{pr_number}")
        add_reviewer(pr_number, REVIEWER_EMAIL)
    else:
        print("No REVIEWER_EMAIL set, skipping reviewer assignment")
    
    return None

def main():
    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable not set")
        return
    
    try:
        pull_requests = get_open_pull_requests()
        print(f"Found {len(pull_requests)} open pull requests")
        
        for pr in pull_requests:
            pr_number = pr["number"]
            pr_title = pr["title"]
            print(f"\nProcessing PR #{pr_number}: {pr_title}")
            
            if is_mergeable(pr_number):
                print("PR is mergeable. Attempting to squash merge...")
                response = merge_pull_request(pr_number, pr_title)
                
                if response.status_code == 200:
                    print(f"Successfully merged PR #{pr_number}")
                else:
                    print(f"Failed to merge PR #{pr_number}. Status code: {response.status_code}")
                    print(f"Response: {response.json()}")
            else:
                result = handle_blocked_pr(pr_number, pr_title)
                if result and result.status_code == 200:
                    print(f"Successfully merged PR #{pr_number} after waiting")
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()