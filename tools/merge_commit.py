import requests
import time
import os
import argparse


# Configuration
GITHUB_TOKEN = os.getenv("QUBIKA_GH_TOKEN")
REPO_OWNER = "manuelqubika"
REPO_NAME = "test-github-actions"

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def get_open_pull_requests():
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls?state=open"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def is_mergeable(pr_number):
    # Sometimes GitHub needs time to calculate mergeability
    max_retries = 3
    retry_delay = 2  # seconds
    
    for _ in range(max_retries):
        url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}"
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
        pr_data = response.json()
        
        # Check if mergeable status is available (might be None initially)
        if pr_data.get("mergeable") is not None:
            return pr_data["mergeable"] and pr_data["mergeable_state"] == "clean"
        
        time.sleep(retry_delay)
    
    return False

def merge_pull_request(pr_number, commit_title):
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/pulls/{pr_number}/merge"
    data = {
        "merge_method": "squash",
        "commit_title": commit_title,
        # Optional: You can add commit_message if needed
    }
    response = requests.put(url, headers=HEADERS, json=data)
    return response

def main():
    try:
        pull_requests = get_open_pull_requests()
        print(f"Found {len(pull_requests)} open pull requests")
        
        for pr in pull_requests:
            pr_number = pr["number"]
            pr_title = pr["title"]
            print(f"\nChecking PR #{pr_number}: {pr_title}")
            
            if is_mergeable(pr_number):
                print("PR is mergeable. Attempting to squash merge...")
                response = merge_pull_request(pr_number, pr_title)
                
                if response.status_code == 200:
                    print(f"Successfully merged PR #{pr_number}")
                else:
                    print(f"Failed to merge PR #{pr_number}. Status code: {response.status_code}")
                    print(f"Response: {response.json()}")
            else:
                print("PR is not mergeable (either not clean or conflicts exist)")
    
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()