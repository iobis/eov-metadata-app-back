# -*- coding: utf-8 -*-
"""
Helper functions and utilities for the metadata app.
"""
import os
import re
import json
import csv
import logging
from logging.handlers import RotatingFileHandler
import requests
from datetime import datetime
from dotenv import load_dotenv
from flask import session, url_for, redirect
from urllib.parse import quote
from config_constants import REPO_OWNER, GITHUB_REPO, JSON_FOLDER

load_dotenv()


# ============================================================================
# Flask Configuration
# ============================================================================

def set_flask_environment(app) -> str:
    """Set the flask development environment.
    Parameters
    ----------
    app: flask.Flask
        The flask application object
    Raises
    ------
    KeyError
        If the FLASK_ENV environment variable is not set.
    Returns
    -------
    str:
        Flask operating environment i.e development
    """
    if os.environ['FLASK_ENV'] == 'production':  # pragma: no cover
        app.config.from_object('config.ProductionConfig')
    elif os.environ['FLASK_ENV'] == 'development':  # pragma: no cover
        app.config.from_object('config.DevelopmentConfig')
    elif os.environ['FLASK_ENV'] == 'test':
        app.config.from_object('config.TestingConfig')

    return os.environ['FLASK_ENV']


# ============================================================================
# Token Management Helpers
# ============================================================================

def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def setup_token_logger():
    """Set up size-limited rotating log for token tracking."""
    token_logger = logging.getLogger('token_tracker')
    token_logger.setLevel(logging.INFO)
    if not token_logger.handlers:
        log_file = os.getenv('TOKEN_LOG_FILE', '/root/metadata-app/token_usage.log')
        max_bytes = _int_env('TOKEN_LOG_MAX_BYTES', 1024 * 1024)  # 1 MiB per file
        backup_count = _int_env('TOKEN_LOG_BACKUP_COUNT', 5)
        handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
        )
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        token_logger.addHandler(handler)
        token_logger.propagate = False
        try:
            os.chmod(log_file, 0o600)
        except Exception:
            pass
    return token_logger


def configure_flask_file_logging(app):
    """
    Attach a rotating file handler to the Flask app logger so app.log cannot grow without bound.

    Only active when FLASK_ENV=production so local development keeps normal console logging.

    Env: APP_LOG_FILE (default: <app.root_path>/app.log),
         APP_LOG_MAX_BYTES (default 5 MiB), APP_LOG_BACKUP_COUNT (default 5).
    """
    if os.environ.get('FLASK_ENV') != 'production':
        return
    if any(isinstance(h, RotatingFileHandler) for h in app.logger.handlers):
        return

    log_path = os.getenv('APP_LOG_FILE', os.path.join(app.root_path, 'app.log'))
    max_bytes = _int_env('APP_LOG_MAX_BYTES', 5 * 1024 * 1024)
    backup_count = _int_env('APP_LOG_BACKUP_COUNT', 5)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8',
    )
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter('%(asctime)s %(levelname)s [%(name)s] %(message)s')
    )
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False
    try:
        os.chmod(log_path, 0o600)
    except Exception:
        pass


def get_token_or_redirect(github, session):
    """
    Simple function to get token from Flask-Dance or redirect to login.
    Flask-Dance handles token storage, so we don't need to store in session.
    
    Returns:
        (token, None) if token exists
        (None, redirect_response) if token is missing
    """
    if not github.authorized:
        return None, redirect(url_for("github.login"))
    
    token = github.token.get("access_token") if github.token else None
    
    if not token:
        # Clear any stale session data
        session.pop("github_oauth_token", None)
        return None, redirect(url_for("github.login"))
    
    return token, None


def github_request(github, session, method, url, **kwargs):
    """
    Wrapper for GitHub API requests that handles token and 401 errors automatically.
    
    Args:
        github: Flask-Dance github blueprint object
        session: Flask session object
        method: HTTP method (get, post, patch, etc.)
        url: API URL
        **kwargs: Additional arguments for requests (json, params, etc.)
    
    Returns:
        (response, None) if successful
        (None, redirect_response) if token missing or 401 error
    """
    # Get token or redirect
    token, redirect_response = get_token_or_redirect(github, session)
    if redirect_response:
        return None, redirect_response
    
    # Add authorization header
    headers = kwargs.pop("headers", {})
    # OAuth access tokens must use Bearer (GitHub REST API); legacy "token" prefix can 401.
    headers["Authorization"] = f"Bearer {token}"
    
    # Make the request
    resp = requests.request(method, url, headers=headers, **kwargs)
    
    # Handle 401 - token expired or revoked
    if resp.status_code == 401:
        # Clear invalid token from session (Flask-Dance will handle its own cleanup)
        session.pop("github_oauth_token", None)
        return None, redirect(url_for("github.login"))
    
    return resp, None


def log_token_creation(github, session, token_logger, token_stats):
    """Log when a new token is created during OAuth flow"""
    if github.authorized and github.token:
        token = github.token.get("access_token")
        if token:
            # Use minimal token preview for logging (first 6 chars only)
            token_preview = f"{token[:6]}..." if len(token) > 6 else "***"
            user = session.get("user", {}).get("login", "unknown")
            token_stats['tokens_created'] += 1
            token_stats['last_token_created'] = datetime.now().isoformat()
            # Log with user info but minimal token exposure
            token_logger.info(f"NEW TOKEN CREATED for user {user} - preview: {token_preview} at {token_stats['last_token_created']}")
            print(f"TOKEN TRACKING: New token created for {user} - {token_preview}", flush=True)


# ============================================================================
# GitHub API Helpers
# ============================================================================

def get_github_issues(github, session, repo_owner, github_repo, token_logger, admin_users=None):
    """Fetch GitHub issues with metadata submission label.

    Uses github_request so invalid/expired OAuth tokens get a 401 -> re-login flow
    instead of an empty dropdown.
    
    Applies access control:
    - Admin users see all issues
    - Regular users see only their own issues

    Args:
        github: Flask-Dance GitHub object
        session: Flask session
        repo_owner: GitHub repo owner
        github_repo: GitHub repo name
        token_logger: Logger for token operations
        admin_users: List of GitHub usernames of admin users, or single string
        
    Returns:
        (list, None) on success (list may be empty if the API returns an error other than 401).
        (None, redirect_response) if not authorized or GitHub returned 401.
    """
    url = f"https://api.github.com/repos/{repo_owner}/{github_repo}/issues"
    params = {"labels": "metadata submission"}
    print("Calling GitHub API for getting issues...", flush=True)
    try:
        response, redirect_response = github_request(
            github, session, "get", url, params=params, timeout=10
        )
        if redirect_response:
            return None, redirect_response
        print("GitHub API responded", flush=True)
        if response.status_code == 200:
            issues = response.json()
            
            # Apply access control filtering
            user = session.get("user")
            if user and admin_users:
                # Filter issues based on user permissions
                filtered_issues = []
                for issue in issues:
                    issue_owner = extract_issue_owner(issue)
                    if can_view_entry(user, issue_owner, admin_users):
                        filtered_issues.append(issue)
                
                print(f"User {user.get('login')} can view {len(filtered_issues)} out of {len(issues)} issues")
                return filtered_issues, None
            
            return issues, None
        print(f"Failed to fetch issues: {response.status_code}")
        token_logger.warning("get_github_issues: GitHub API status %s", response.status_code)
        return [], None
    except Exception as e:
        print(f"Error fetching issues: {e}")
        token_logger.warning("get_github_issues: %s", e)
        return [], None


def fetch_projects_from_github():
    """Fetch the list of projects from the csv in the GitHub repository"""
    csv_url = "https://raw.githubusercontent.com/{REPO_OWNER}/{GITHUB_REPO}/refs/heads/main/data/bioeco_list.csv"
    projects = []
    try:
        response = requests.get(csv_url, timeout=10)
        response.raise_for_status()
        decoded_content = response.content.decode('utf-8')
        reader = csv.DictReader(decoded_content.splitlines())
        
        for row in reader:
            # Expecting columns: 'name', 'project_link'
            projects.append({
                "name": row.get("Project Name", "Unnamed"),
                "project_link": row.get("URL", "")
            })
        # Sort projects alphabetically by name (case-insensitive)
        projects.sort(key=lambda x: x["name"].lower())
        return projects
    except Exception as e:
        print(f"Error fetching or parsing CSV: {e}")
        return []


# ============================================================================
# User Management Helpers
# ============================================================================

def get_or_fetch_user(github, session):
    """
    Get user from session or fetch from GitHub API.
    Returns user dict or None if unable to fetch.
    """
    user = session.get("user")
    if not user:
        try:
            resp = github.get("/user", timeout=10)
            if resp.ok:
                user_info = resp.json()
                session["user"] = user_info
                print("User Info Fetched and Saved:", session["user"], flush=True)
                return user_info
        except Exception as e:
            print(f"Error fetching user: {e}", flush=True)
    return user


# ============================================================================
# JSON/Data Processing Helpers
# ============================================================================

def extract_json_blocks(issue_body):
    """Extract JSON blocks from GitHub issue body."""
    # Find all blocks between ```json ... ``` 
    blocks = re.findall(r"### (.*?)\n```json\n(.*?)\n```", issue_body, re.DOTALL)
    result = {}
    for header, json_str in blocks:
        try:
            result[header.strip()] = json.loads(json_str)
        except Exception as e:
            result[header.strip()] = None
    return result


def strip_schema_org_prefixes(obj):
    """
    Recursively strip a leading 'schema:' from dict keys so JSON-LD from GitHub
    matches processMappings paths (e.g. schema:legalName -> legalName,
    schema:geosparql:asWKT -> geosparql:asWKT).
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            new_key = k[7:] if isinstance(k, str) and k.startswith("schema:") else k
            out[new_key] = strip_schema_org_prefixes(v)
        return out
    if isinstance(obj, list):
        return [strip_schema_org_prefixes(x) for x in obj]
    return obj


def split_metadata_submission_graph(output):
    """
    Split a single combined @graph submission into Project, Action, and metadata-frequency nodes.
    Order in the graph is not assumed; @type and presence of frequency are used.
    """
    graph = output.get("@graph") if isinstance(output, dict) else None
    if not graph:
        return None, None, {}

    project = None
    action = None
    frequency = {}

    for node in graph:
        if not isinstance(node, dict):
            continue
        t = node.get("@type", "")
        if isinstance(t, str):
            if project is None and (
                t == "Project"
                or t == "ResearchProject"
                or "ResearchProject" in t
            ):
                project = node
            elif action is None and "Action" in t:
                action = node
        if "frequency" in node or "schema:frequency" in node:
            frequency = node

    if project is None and graph:
        project = graph[0]
    if action is None and len(graph) > 1:
        for node in graph[1:]:
            if isinstance(node, dict) and node.get("@type") and "Action" in str(node.get("@type")):
                action = node
                break

    return project, action, frequency


# ============================================================================
# Error Handling Helpers
# ============================================================================

def redirect_to_error(error_message, details=None):
    """
    Helper function to redirect to error page with a message.
    Usage: return redirect_to_error("Something went wrong", "Additional details")
    """
    error_url = url_for('error_page', error=error_message)
    if details:
        error_url += f"&details={quote(str(details))}"
    return redirect(error_url)


# ============================================================================
# Access Control Helpers
# ============================================================================

def is_admin(user, admin_users):
    """
    Check if a user is an admin/app owner.
    
    Args:
        user: User dict from GitHub (should have 'login' key)
        admin_users: List of GitHub usernames that are admins, or a single string
        
    Returns:
        bool: True if user is admin, False otherwise
    """
    if not user:
        return False
    
    # Handle both single string and list of admins for backwards compatibility
    if isinstance(admin_users, str):
        admin_list = [admin_users]
    else:
        admin_list = admin_users if admin_users else []
    
    return user.get("login") in admin_list


def can_view_entry(user, entry_owner, admin_users):
    """
    Check if a user can view/access an entry.
    
    Rules:
    - Admins can view all entries
    - Regular users can only view their own entries (or if listed as owner)
    
    Args:
        user: User dict from GitHub (should have 'login' key)
        entry_owner: GitHub username(s) of the entry creator. Can be:
                     - Single string: "username"
                     - Comma-separated: "user1, user2"
                     - List: ["user1", "user2"]
        admin_users: List of GitHub usernames that are admins, or a single string
        
    Returns:
        bool: True if user can access the entry, False otherwise
    """
    if not user:
        return False
    
    user_login = user.get("login")
    
    # Admins can view all entries
    if is_admin(user, admin_users):
        return True
    
    # Regular users can view if they're listed as owners
    # Handle different formats: single string, comma-separated, or list
    if entry_owner is None:
        return False
    
    # Convert to list of usernames
    if isinstance(entry_owner, list):
        owners = [u.strip() for u in entry_owner]
    elif isinstance(entry_owner, str):
        # Handle comma-separated usernames
        owners = [u.strip() for u in entry_owner.split(",")]
    else:
        return False
    
    return user_login in owners


def extract_issue_owner(issue):
    """
    Extract the owner/creator of a GitHub issue.
    
    Args:
        issue: GitHub issue object from API response
        
    Returns:
        str: GitHub username of the issue creator
    """
    # Try to get user login from issue.user.login (API response format)
    if issue.get("user") and issue["user"].get("login"):
        return issue["user"]["login"]
    
    # Fallback: try to extract from issue body if stored
    # This is useful if owner is manually stored in the issue body
    body = issue.get("body", "")
    if "bioeco-created-by: " in body:
        # Extract owner from custom field in body
        for line in body.split("\n"):
            if "bioeco-created-by: " in line:
                return line.split("bioeco-created-by: ")[1].strip()
    
    return None


def load_bioeco_entries_with_access_control(user, admin_users):
    """
    Load bioeco entries from program_names.txt with access control filtering.
    
    Entries are loaded from program_names.txt (which maps to GitHub folders).
    Access control is determined by bioeco_creators.json mapping.
    
    Args:
        user: User dict from GitHub (should have 'login' key)
        admin_users: List of GitHub usernames that are admins, or a single string
        
    Returns:
        list: Filtered list of bioeco entries user can access
    """
    bioeco_entries = []
    bioeco_creators = {}
    
    try:
        # Load bioeco creator metadata if it exists
        try:
            with open("bioeco_creators.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                bioeco_creators = data.get("creators", {})
        except FileNotFoundError:
            print("bioeco_creators.json not found - all bioeco entries will be accessible to admin only")
        except json.JSONDecodeError:
            print("Error parsing bioeco_creators.json")
        
        # Load program names from local file (corresponds to GitHub folder names)
        try:
            with open("program_names.txt", "r", encoding="utf-8") as f:
                programs = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print("program_names.txt not found - no BioEco entries available")
            return []
        
        for i, folder_name in enumerate(programs):
            entry_key = f"bioeco-{i}"
            creator = bioeco_creators.get(entry_key, None)
            
            # Apply access control
            if creator is None:
                if not is_admin(user, admin_users):
                    continue  # Skip unassigned entries for non-admin users
            elif not can_view_entry(user, creator, admin_users):
                continue  # Skip entries user doesn't have access to
            
            # Create entry with folder name and display name
            entry = {
                "number": entry_key,
                "title": folder_name,
                "is_bioeco": True,
                "bioeco_index": i,
                "folder": folder_name,  # Folder name (used for fetching JSON)
                "user": {
                    "login": creator if creator else "unassigned"
                }
            }
            bioeco_entries.append(entry)
    except Exception as e:
        print(f"Error loading bioeco entries: {e}")
    
    return bioeco_entries