from datetime import datetime
import json
import base64
import requests
import os
from flask import jsonify, request, session, redirect, url_for
from helpers import github_request

# Function to handle the action based on the form submission
def process_submission_action(issue_number, action, output, GITHUB_API_URL, REPO_OWNER, GITHUB_REPO, github, session): 
    if action == "print_json":
        # Print JSON for testing
        print(output)
        return jsonify({"success": True, "printed_json": output})
    
    # Extract title from the first item in @graph (schema_entry)
    schema_entry = output["@graph"][0]
    issue_title = f"New Submission: {schema_entry.get('schema:name') or schema_entry.get('schema:legalName') or 'Untitled EOV Metadata Entry'}"
    
    # Get the current user who is creating the issue
    user = session.get("user")
    created_by = user.get("login") if user else "unknown"
    created_at = datetime.now().isoformat()
    
    # Prepare issue body with full @graph output and ownership metadata
    issue_body = (
        "### Metadata Submission\n"
        "```json\n"
        f"{json.dumps(output, indent=2)}\n"
        "```\n"
    )

    labels = ["draft submission", "metadata submission"] if action == "save_draft" else ["metadata submission"]

    # Create payload for GitHub with full output
    payload = {
        "title": issue_title,
        "body": issue_body,
        "labels": labels
    }
    print("Payload:", payload)
    
    # Save a draft to GitHub
    if action == "save_draft":
        # Create a new issue labeled as Draft
        response, redirect_response = github_request(
            github, session, "post",
            GITHUB_API_URL.format(owner=REPO_OWNER, repo=GITHUB_REPO),
            json=payload
        )
        if redirect_response:
            return {"success": False, "error": "Authentication required", "reauth_required": True}, 401
        
        if response.status_code == 201:
            issue_url = response.json()["html_url"]
            if "draft submission" not in [lbl["name"] for lbl in response.json().get("labels", [])]:
                print("User does not have permission to add labels. Using admin token as fallback.")
                fallback_add_labels(response.json().get("number"), REPO_OWNER, GITHUB_REPO, labels[0])
            return {"success": True, "message": f"Draft saved successfully and assigned to {created_by}!", "issue_url": issue_url}
        else:
            return {"success": False, "error": response.json()}
    
    # Submit to GitHub API
    if action == "submit_to_github":
        response, redirect_response = github_request(
            github, session, "post",
            GITHUB_API_URL.format(owner=REPO_OWNER, repo=GITHUB_REPO),
            json=payload
        )
        if redirect_response:
            return {"success": False, "error": "Authentication required", "reauth_required": True}, 401

        # Log the response for debugging
        print(f"GitHub API Response Status: {response.status_code}")
        print(f"Response Body: {response.text}")

        # Check the response from GitHub
        if response.status_code == 201:
            issue_url = response.json()["html_url"]
            if "metadata submission" not in [lbl["name"] for lbl in response.json().get("labels", [])]:
                print("User does not have permission to add labels. Using admin token as fallback.")
                fallback_add_labels(response.json().get("number"), REPO_OWNER, GITHUB_REPO, labels[0])
            return {"success": True, "message": f"Issue submitted successfully and assigned to {created_by}!", "issue_url": issue_url}
        else:
            return {"success": False, "error": response.json()}, response.status_code

    # Update issue using GitHub API
    if action == "update_github" and issue_number is not None:
        print("issue_number", issue_number)
        
        if issue_number.startswith("bioeco-"):
            # Handle BioEco update - folder name is in session
            folder = session.get('bioeco_folder')
            if not folder:
                return {"success": False, "error": "BioEco folder information not found in session"}
            
            # Get the full graph from output
            graph = output.get("@graph", [])
            if not graph:
                return {"success": False, "error": "Invalid output for BioEco update"}
            
            # Update single JSON file with the full graph
            json_api_url = f"https://api.github.com/repos/BioEcoOcean/metadata-tracking-dev/contents/jsonFiles/{folder}/{folder}.json"
            resp, redirect_response = github_request(github, session, "get", json_api_url)
            if redirect_response:
                return {"success": False, "error": "Authentication required", "reauth_required": True}, 401
            if resp.status_code != 200:
                return {"success": False, "error": "Failed to get current BioEco file"}
            
            current = resp.json()
            sha = current.get('sha')
            if not sha:
                return {"success": False, "error": "Missing SHA for current BioEco file"}
            
            content_data = {"@graph": graph}
            content = base64.b64encode(json.dumps(content_data, indent=2).encode()).decode()
            payload = {
                "message": f"Update BioEco entry {folder}",
                "content": content,
                "sha": sha
            }
            resp, redirect_response = github_request(github, session, "put", json_api_url, json=payload)
            if redirect_response:
                return {"success": False, "error": "Authentication required", "reauth_required": True}, 401
            if resp.status_code not in [200, 201]:
                return {"success": False, "error": resp.json()}
            
            return {"success": True, "message": f"BioEco entry {folder} updated successfully!"}
        else:
            # Original issue update
            issue_url = f"https://api.github.com/repos/{REPO_OWNER}/{GITHUB_REPO}/issues/{issue_number}"
            response, redirect_response = github_request(
                github, session, "patch",
                issue_url,
                json=payload
            )
            if redirect_response:
                return {"success": False, "error": "Authentication required", "reauth_required": True}, 401

            if response.status_code == 200:
                # Step 2: Add a comment to the issue (POST request)
                comments_url = f"https://api.github.com/repos/{REPO_OWNER}/{GITHUB_REPO}/issues/{issue_number}/comments"
                comment_payload = {
                    "body": f"Entry updated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"  # Add a timestamp for the update
                }
                comment_response, redirect_response = github_request(
                    github, session, "post",
                    comments_url,
                    json=comment_payload
                )
                if redirect_response:
                    return {"success": False, "error": "Authentication required", "reauth_required": True}, 401

                # Check if the comment was added successfully
                if comment_response.status_code == 201:
                    issue_url = f"https://github.com/{REPO_OWNER}/{GITHUB_REPO}/issues/{issue_number}"
                    return {"success": True, "message": "Issue updated and comment added successfully!", "issue_url": issue_url}
                else:
                    return {"success": False, "error": comment_response.json()}
            else:
                return {"success": False, "error": response.json()}, response.status_code

    return {"success": False, "error": "Invalid action provided"}

# handle label assignment using the admin token:
def fallback_add_labels(issue_number, REPO_OWNER, GITHUB_REPO, label):
    admin_token = os.getenv('ADMIN_GITHUB_TOKEN')  # Admin token stored securely in environment variables
    if not admin_token:
        print("Admin token not configured. Unable to add labels.")
        return

    headers = {"Authorization": f"token {admin_token}"}
    label_url = f"https://api.github.com/repos/{REPO_OWNER}/{GITHUB_REPO}/issues/{issue_number}"
    payload = {"labels": [label]}

    response = requests.patch(label_url, json=payload, headers=headers)
    if response.status_code == 200:
        print(f"Labels added successfully to issue #{issue_number}.")
    else:
        print(f"Failed to add labels to issue #{issue_number}. Response: {response.json()}")
