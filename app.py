from flask import Flask, session, render_template, request, jsonify, url_for, redirect, send_file, flash


from flask_dance.contrib.github import make_github_blueprint, github
from flask_session import Session
#from redis import Redis
import os
import requests
import tempfile
import zipfile
import json
import pandas as pd
import re
import csv
import io
import platform #for running locally
from flask_caching import Cache
from datetime import datetime, timedelta
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.exceptions import HTTPException
from urllib.parse import quote, unquote
import logging
#### Custom imports
from helpers import (
    set_flask_environment,
    setup_token_logger,
    configure_flask_file_logging,
    log_token_creation,
    get_github_issues,
    fetch_projects_from_github,
    get_or_fetch_user,
    extract_json_blocks,
    strip_schema_org_prefixes,
    split_metadata_submission_graph,
    redirect_to_error,
    get_token_or_redirect,
    github_request,
    is_admin,
    can_view_entry,
    extract_issue_owner,
    load_bioeco_entries_with_access_control
)
from config_constants import (
    REPO_OWNER,
    BRANCH,
    JSON_FOLDER,
    GITHUB_REPO,
    GITHUB_API_URL,
    RAW_BASE_URL,
    EOV_USER,
    EOV_PASS,
    ADMIN_USERS
)
from mappings import schema_field_mapping, actions_field_mapping, frequency_field_mapping
from processMappings import map_form_to_schema
from generateForm import generate_form
from submitAction import process_submission_action
from makeFormIntoJson import makeFormJson
from datetime import datetime
from helpers import set_flask_environment
from werkzeug.middleware.proxy_fix import ProxyFix
from dois import ObisDoi
from convert_to_dwc import convert_to_dwc as run_dwc_conversion
from urllib.parse import quote, unquote

# ============================================================================
# Application Setup
# ============================================================================
app = Flask(__name__)
set_flask_environment(app=app)
configure_flask_file_logging(app)
# Add ProxyFix middleware to handle headers from Nginx
app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

# app.secret_key = os.environ.get("SECRET_KEY", "supersekrit")
# app.config["GITHUB_OAUTH_CLIENT_ID"] = os.environ.get("GITHUB_OAUTH_CLIENT_ID")
# app.config["GITHUB_OAUTH_CLIENT_SECRET"] = os.environ.get("GITHUB_OAUTH_CLIENT_SECRET")
# app.config['SESSION_TYPE'] = "redis"
# app.config['SESSION_REDIS'] = Redis(host='127.0.0.1', port=5000)
# app.config['SESSION_PERMANENT'] = False
# app.config['SESSION_USE_SIGNER'] = True
# Session(app)

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Set up the OAuth
github_blueprint=make_github_blueprint(
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    scope="public_repo"
#    redirect_url="https://eovmetadata.obis.org/login/github/authorized"
    )
app.register_blueprint(github_blueprint, url_prefix="/login")

# ============================================================================
# Token Management Setup
# ============================================================================
token_logger = setup_token_logger()
_token_stats = {
    'tokens_created': 0,
    'tokens_validated': 0,
    'tokens_refreshed': 0,
    'tokens_failed': 0,
    'token_usage_count': {},
    'last_token_created': None
}

# Removed get_github_token_wrapper - use get_token_or_redirect or github_request instead

# ============================================================================
# App routes
# ============================================================================
@app.route("/")
def index():
    """ Landing page"""
    print("User Session  landing route:", session, flush=True)
    if not github.authorized:
        return render_template("landing.html", user=None)
    
    user = get_or_fetch_user(github, session)
    if not user:
        return redirect(url_for('index'))
    return redirect(url_for("home"))

@app.route('/github/authorized')
def github_authorized():
    """Handle the OAuth callback from GitHub."""
    if not github.authorized:
        # Redirect to login if not authorized
        return redirect(url_for("github.login"))

    # Log token creation
    log_token_creation(github, session, token_logger, _token_stats)

    # Fetch user info from GitHub
    resp = github.get("/user")
    print("GitHub user Info:", resp, flush=True)
    if not resp.ok:
        token_logger.error(f"Failed to fetch user info after OAuth: {resp.status_code}")
        return redirect(url_for('index')) 

    # Store user info in session
    user_info = resp.json()
    session["user"] = user_info
    
    # Token is already stored by Flask-Dance, no need to store separately
    token, _ = get_token_or_redirect(github, session)
    if token:
        # Don't log full token preview in console output
        print(f"User Info & token Saved: {user_info.get('login')}", flush=True)
    
    return redirect(url_for('home'))

@app.route("/data")
def data():
    return render_template("data.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/dataproducer")
def dataproducer():
    user = get_or_fetch_user(github, session)
    if not user:
        return redirect(url_for('index'))
    
    # Get token or redirect - simple check
    token, redirect_response = get_token_or_redirect(github, session)
    if redirect_response:
        return redirect_response

    projects = cache.get('projects')
    if projects is None:
        projects = fetch_projects_from_github()
        cache.set('projects', projects, timeout=60*60)  # Cache for 1 hour
    return render_template("metadata-landing.html", user=session.get("user"), projects=projects)

@app.route("/home")
def home():
    """Main page, also display list of current programs submitted."""
    if not github.authorized:
        return redirect(url_for("github.login"))
    
    # Fetch user data from session instead of making a new GitHub API request
    print("GitHub Authorized:", github.authorized, flush=True)
    print("Session User homeroute:", session.get("user"), flush=True)

    user = get_or_fetch_user(github, session)
    if not user:
        return redirect(url_for('index'))
    
    # Get token or redirect - simple check
    token, redirect_response = get_token_or_redirect(github, session)
    if redirect_response:
        return redirect_response
    
    return render_template("home.html", user=session.get("user"), admin_users=ADMIN_USERS)

        # Fetch user info from GitHub if not in session
        resp = github.get("/user")
        if not resp.ok:
            return redirect(url_for('index'))
        
        user_info = resp.json()
        session["user"] = user_info
        print("User Info Fetched and Saved:", session["user"], flush=True)
    
    # Retrieve the token from the session
    github_token = session.get("GITHUB_TOKEN")
    if not github_token:
        github_token = session.get("github_oauth_token", {}).get("access_token")
        if github_token:
            session["GITHUB_TOKEN"] = github_token
    print("GITHUB_TOKEN from session:", github_token, flush=True)
    
    return render_template("home.html", user=session.get("user"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

def get_github_issues():
    GITHUB_TOKEN = session.get("github_oauth_token", {}).get("access_token")
    try:
        url = f"https://api.github.com/repos/{REPO_OWNER}/{GITHUB_REPO}/issues"
        headers = {"Authorization": f"token {GITHUB_TOKEN}"}
        params = {"labels": "metadata submission"}  # Filtering by label
        print("Calling GitHub API for getting issues...", flush=True)
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print("GitHub API responded", flush=True)
        if response.status_code == 200:
            return response.json()  # Return the list of issues
        else:
                print(f"Failed to fetch issues: {response.status_code}")
                return []  # Return an empty list in case of failure
    except Exception as e:
        print(f"Error fetching issues: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/handle_form_submission", methods=["GET", "POST"])
def handle_form_submission():
    print(request.method)
    if request.method == "GET":
        return render_template("new_submission.html", form_html=generate_form(prefilled_data=None))
    elif request.method == "POST":
        return makeFormJson()
    return None
 
@app.route("/submit", methods=["POST"])
def handle_submission():
    # Get the form data (action and schema_entry)
    action = request.form.get("action")
    schema_entry, actions_json, metadata_frequency = makeFormJson()  #pass the form output to makeFormJson function
    print("attempting to get issue number")
    print("session issue number: ", session.get('issue_number', 'N/A'))
    
    GITHUB_TOKEN = session.get("github_oauth_token", {}).get("access_token")
    print("submission token: ", GITHUB_TOKEN)
    if not GITHUB_TOKEN:
        return jsonify({"success": False, "error": "GitHub token not found in session"}), 401
    # Check if the token has the required scopes
    required_scopes = ["public_repo"]
    if not check_github_token_scopes(GITHUB_TOKEN, required_scopes):
        return jsonify({"success": False, "error": "GitHub token does not have the required scopes"}), 403

    # Call the function to process the action, passing all 3 json objects
    result = process_submission_action(
        session.get('issue_number', None), 
        action, 
        schema_entry, actions_json, metadata_frequency,
        GITHUB_API_URL, REPO_OWNER, GITHUB_REPO)
    print("ACTION RESULT: ", result)
    
    # Handle print_json action
    if action == "print_json":
        return render_template("print_json.html", 
        schema_entry=json.dumps(schema_entry, indent=4),
        actions_json=json.dumps(actions_json, indent=4),
        metadata_frequency=json.dumps(metadata_frequency, indent=4))

    # Handle save draft action
    if action == "save_draft":
        # Check if re-authentication is required
        if isinstance(result, tuple) and len(result) == 2:
            result_dict, status_code = result
            if result_dict.get("reauth_required"):
                result_dict["reauth_url"] = url_for("github.login")
                return jsonify(result_dict), status_code
        elif isinstance(result, dict) and result.get("reauth_required"):
            result["reauth_url"] = url_for("github.login")
            return jsonify(result), 401
        
        if result.get("success"):
            message = result.get("message", "Draft saved successfully!")
            issue_url = result.get("issue_url")
            return render_template("success.html", message=message, issue_url=issue_url)
        else:
            error_message = result.get("error", "An unexpected error occurred.")
            error_details = result.get("details", None)
            return redirect_to_error(error_message, error_details)

    # Return the appropriate response based on the result from the function
    if action in ["submit_to_github", "update_github"]:  # Check if the action was a submission
        # Check if re-authentication is required
        if isinstance(result, tuple) and len(result) == 2:
            result_dict, status_code = result
            if result_dict.get("reauth_required"):
                result_dict["reauth_url"] = url_for("github.login")
                return jsonify(result_dict), status_code
        elif isinstance(result, dict) and result.get("reauth_required"):
            result["reauth_url"] = url_for("github.login")
            return jsonify(result), 401
        
        if result.get("success"):
            message = result.get("message", "Action completed successfully!")
            issue_url = result.get("issue_url")
            return render_template("success.html", message=message, issue_url=issue_url)
        else:
            error_message = result.get("error", "An unexpected error occurred.")
            error_details = result.get("details", None)  # Include additional details if available
            return redirect_to_error(error_message, error_details)
    else:
        return result

@app.route("/success")
def success():
    message = request.args.get("message", "Entry submitted successfully.")
    return render_template("success.html", message=message)

@app.route("/update_entry", methods=["GET", "POST"])
def update_entry():
    print(">>> ", request.method)
    issues, redirect_response = get_github_issues(
        github, session, REPO_OWNER, GITHUB_REPO, token_logger, admin_users=ADMIN_USERS
    )
    if redirect_response:
        return redirect_response
    filtered_issues = [
        issue for issue in issues
        if any(label["name"] in ["metadata submission", "draft submission"] for label in issue.get("labels", []))
    ]

    if request.method == "GET":
        return render_template("update_entry.html", issues=filtered_issues)

    elif request.method == "POST":
        print(request.get_data())
        # Fetch the selected issue
        print(str(request))
        print('setting default value')
        print("session issue number after setting default value: ", session.get('issue_number', 'N/A'))
        issue_number = request.form.get("selected_issue", 'N/A')
        if issue_number:
            # Get the GitHub issue data
            print("issue number: ", issue_number, "type: ", type(issue_number), "request: ", request.method)
            session['issue_number'] = issue_number
            print("session issue number after setting it with real value: ", session.get('issue_number', 'N/A'))
            issue_url = f"https://api.github.com/repos/{REPO_OWNER}/{GITHUB_REPO}/issues/{issue_number}"
            headers = {"Authorization": f"token {GITHUB_TOKEN}"}
            #print("Calling GitHub API in update entry route...", flush=True) #debugging
            response = requests.get(issue_url, headers=headers, timeout=10)
            #print("GitHub API responded", flush=True)
            response_data = response.json()  # Debug: Inspect the full response from GitHub
            print(f"Response Data: {response_data}")

            if response.status_code == 200:
                # Parse the issue data
                issue_data = response.json()
                issue_body = issue_data["body"]
                json_blocks = extract_json_blocks(issue_body)
                schema_entry = json_blocks.get("Metadata Submission")
                actions_json = json_blocks.get("Actions JSON")
                metadata_frequency = json_blocks.get("Metadata Frequency")

                # Map the GitHub issue data to schema format
                mapped_schema_entry = map_form_to_schema(schema_entry, schema_field_mapping)
                mapped_actions_entry = map_form_to_schema(actions_json, actions_field_mapping)
                mapped_metadata_frequency = map_form_to_schema(metadata_frequency, frequency_field_mapping)
                form_html = generate_form(prefilled_data=mapped_schema_entry,
                    actions_data=mapped_actions_entry,
                    frequency_data=mapped_metadata_frequency)

                return render_template("update_entry.html", issues=filtered_issues, form_html=form_html, issue_number=issue_number)
            else:
                return jsonify({"success": False, "error": response.json()})
        else:
            return jsonify({"success": False, "error": "No issue selected."})

@app.route("/remove_entry", methods=["GET", "POST"])
def remove_entry():
    if not github.authorized:
        return redirect(url_for("github.login"))

    user = get_or_fetch_user(github, session)
    if not user:
        return redirect(url_for('index'))

    # Get token or redirect - simple check
    token, redirect_response = get_token_or_redirect(github, session)
    if redirect_response:
        return redirect_response
    headers = {"Authorization": f"Bearer {token}"}
    username = user.get("login")

    # Fetch issues created by this user with the "metadata submission" label
    params = {"creator": username, "labels": "metadata submission"}
    response = requests.get(GITHUB_API_URL, headers=headers, params=params, timeout=10)
    issues = response.json() if response.status_code == 200 else []

    if request.method == "POST":
        issue_number = request.form.get("selected_issue")
        if not issue_number:
            return render_template("remove_entry.html", issues=issues, error="No issue selected.")

        # Update labels on the selected issue
        issue_url = f"{GITHUB_API_URL}/{issue_number}"
        # Get current labels
        issue_resp = requests.get(issue_url, headers=headers, timeout=10)
        if issue_resp.status_code != 200:
            return render_template("remove_entry.html", issues=issues, error="Could not fetch issue details.")

        current_labels = [label["name"] for label in issue_resp.json().get("labels", [])]
        # Remove "metadata submission", add "remove entry"
        new_labels = [l for l in current_labels if l != "metadata submission"]
        if "remove entry" not in new_labels:
            new_labels.append("remove entry")

        patch_resp = requests.patch(issue_url, headers=headers, json={"labels": new_labels})
        if patch_resp.status_code == 200:
            return render_template("success.html", issue_url=issue_url, message="Entry marked for removal.")
        else:
            return render_template("remove_entry.html", issues=issues, issue_url=issue_url, error="Failed to update issue labels.")

    return render_template("remove_entry.html", issues=issues)


@app.route('/generate_doi', methods=['POST'])
def generate_doi():
    data = request.json
    doi_obj = ObisDoi()
    
    # Set basic info
    doi_obj.title = data.get('title')
    doi_obj.url = data.get('url')
    
    # Set creators info (now supports multiple)
    creators_data = data.get('creators', [])
    if creators_data:
        doi_obj.creators = []
        for creator in creators_data:
            creator_entry = {
                "name": creator.get('name'),
                "nameType": creator.get('nameType', 'Organizational')
            }
            
            # Add given/family names for Personal type
            if creator.get('nameType') == 'Personal':
                if creator.get('givenName'):
                    creator_entry['givenName'] = creator.get('givenName')
                if creator.get('familyName'):
                    creator_entry['familyName'] = creator.get('familyName')
            
            doi_obj.creators.append(creator_entry)
    else:
        # Fallback to default OBIS creator if no creators provided
        doi_obj.creators = [{
            "name": "Ocean Biodiversity Information System (OBIS)",
            "nameType": "Organizational",
        }]
    
    # Set publisher
    doi_obj.publisher = data.get('publisher', 'Ocean Biodiversity Information System (OBIS)')
    
    try:
        result = doi_obj.reserve()
        # DataCite returns the DOI in result['data']['id']
        if 'data' in result and 'id' in result['data']:
            return jsonify({'doi': result['data']['id']})
        else:
            return jsonify({'error': result}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/process_file", methods=["POST"])
def process_file():
    file = request.files.get("file")
    url = request.form.get("url")

    try:
        sheet_data = {}

        if file:
            if file.filename.endswith((".xls", ".xlsx", ".ods")):
                xls = pd.ExcelFile(file)
                for sheet in xls.sheet_names:
                    df = xls.parse(sheet, nrows=5)
                    sheet_data[sheet] = {
                        "headers": list(df.columns),
                        "rows": df.fillna("").values.tolist()  # convert to list of lists
                    }
            else:
                df = pd.read_csv(file, sep=None, engine="python", nrows=5)
                sheet_data["Sheet1"] = {  ##Probably change name of this
                    "headers": list(df.columns),
                    "rows": df.fillna("").values.tolist()
                }

        elif url:
            import io, requests
            r = requests.get(url)
            r.raise_for_status()
            content = io.BytesIO(r.content)

            if url.endswith((".xls", ".xlsx", ".ods")):
                xls = pd.ExcelFile(content)
                for sheet in xls.sheet_names:
                    df = xls.parse(sheet, nrows=5)
                    sheet_data[sheet] = {
                        "headers": list(df.columns),
                        "rows": df.fillna("").values.tolist()
                    }
            else:
                df = pd.read_csv(io.StringIO(r.text), sep=None, engine="python", nrows=5)
                sheet_data["Sheet1"] = {
                    "headers": list(df.columns),
                    "rows": df.fillna("").values.tolist()
                }

        else:
            return jsonify({"error": "No file or URL provided"}), 400

        return jsonify({"sheets": sheet_data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/convert_to_dwc", methods=["POST"])
def convert_to_dwc_route():
    file = request.files.get("file")
    if not file:
        return jsonify({"error": "No file uploaded or file not in expected format"}), 400

    try:
        # Create temporary directories
        with tempfile.TemporaryDirectory() as tmpdir:
            upload_path = os.path.join(tmpdir, file.filename)
            file.save(upload_path)
            print("Upload path: ", upload_path)

            #output_path = os.path.join(tmpdir, f"{os.path.splitext(file.filename)[0]}_dwc.csv")
            #print("Output path: ", output_path)
            try:
                output_files = run_dwc_conversion(upload_path, tmpdir)
            except Exception as e:
                return jsonify({"error": f"Python script failed:\n{str(e)}"}), 500
            # commented out the part that handles R files since switched to python for now
            # # Pass tmpdir to R
            # result = subprocess.run(
            #     [R_PATH, "static/scripts/convert_to_dwc.R", upload_path, tmpdir],
            #     capture_output=True,
            #     text=True
            # )

            # if result.returncode != 0:
            #     return jsonify({"error": f"R script failed:\n{result.stderr}"}), 500

            # # Gather CSV files
            # output_files = sorted([os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".csv")])
            previews = {}
            for f in output_files:
                df = pd.read_csv(f)
                previews[os.path.basename(f)] = df.head().to_html(classes="table table-striped", index=False)

            # Create ZIP of all CSVs
            zip_filename = f"dwc_files_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
            zip_path = os.path.join(tempfile.gettempdir(), zip_filename)
            with zipfile.ZipFile(zip_path, "w") as zipf:
                for f in output_files:
                    zipf.write(f, arcname=os.path.basename(f))
            
            # Return preview + download links
            return jsonify({
                "previews": previews,
                "files": url_for("download_tmp", path=quote(zip_path))
            })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/download_tmp")
def download_tmp():
    file_path = request.args.get("path")
    if not file_path or not os.path.exists(file_path):
        return "File not found", 404
    file_path = unquote(file_path)
    if not os.path.exists(file_path):
        return "File not found", 404
    return send_file(file_path, as_attachment=True)

####### EOV pages #######
@app.route("/eov/<eov>", methods=["GET", "POST"])
def eov_page(eov):
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")
        if user == EOV_USER and pw == EOV_PASS:
            session["eov_logged_in"] = True
            return redirect(url_for("eov_page", eov=eov))
        else:
            flash("Invalid username or password", "error")

    logged_in = session.get("eov_logged_in", False)

    template_path = f"eov/{eov}.html"
    try:
        return render_template(template_path, eov=eov, logged_in=logged_in)
    except:
        return f"<h2>No page found for EOV: {eov}</h2>", 404


####### Helper functions ########
def fetch_projects_from_github():
    """Fetch the list of projects from the csv in the GitHub repository"""
    csv_url = "https://raw.githubusercontent.com/BioEcoOcean/metadata-tracking-dev/refs/heads/main/data/bioeco_list.csv"
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
        print(f"Error fetching BioEco JSON for {folder_name}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/token_status")
def token_status():
    """
    Route to check token status and statistics.
    Useful for debugging token issues.
    
    SECURITY: Requires authentication. Only shows user's own token info.
    For admin-level stats, use /token_status/admin (if enabled).
    """
    # Require authentication - no stats for unauthorized users
    if not github.authorized:
        return jsonify({
            "authorized": False,
            "message": "Not authorized. Please log in."
        }), 401
    
    # Simple token check - no validation needed
    token, redirect_response = get_token_or_redirect(github, session)
    if redirect_response:
        return jsonify({
            "authorized": False,
            "token_valid": False,
            "message": "Not authenticated. Please log in."
        }), 401
    
    # Get token info from GitHub - only for current user
    token_info = {}
    user_info = session.get("user", {})
    if token:
        try:
            response, redirect_response = github_request(github, session, "get", "https://api.github.com/user", timeout=5)
            if redirect_response:
                return jsonify({
                    "authorized": False,
                    "token_valid": False,
                    "message": "Token expired. Please log in again."
                }), 401
            if response.status_code == 200:
                scopes = response.headers.get("X-OAuth-Scopes", "")
                token_info = {
                    "scopes": scopes.split(", ") if scopes else [],
                    "rate_limit_remaining": response.headers.get("X-RateLimit-Remaining", "unknown"),
                    "rate_limit_reset": response.headers.get("X-RateLimit-Reset", "unknown")
                }
        except Exception as e:
            token_info = {"error": "Unable to fetch token info"}
    
    # Only return user's own token info, not system-wide stats
    return jsonify({
        "authorized": True,
        "token_valid": token is not None,
        "user": user_info.get("login", "unknown"),
        "token_info": token_info,
        "has_token": True
    })

@app.route("/error")
def error_page():
    """
    Route to manually display an error page.
    Can be used with query parameters: ?error=message&details=details
    """
    error_message = request.args.get("error", "An error occurred")
    error_details = request.args.get("details", None)
    return render_template("error.html", error=error_message, details=error_details)

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors"""
    return render_template("error.html", 
                         error="Page not found (404)",
                         details=f"The page you're looking for doesn't exist. URL: {request.url}"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 Internal Server errors"""
    # Log the error
    app.logger.error(f"Internal Server Error: {str(error)}", exc_info=True)
    return render_template("error.html",
                         error="Internal Server Error (500)",
                         details="An unexpected error occurred. Please try again later."), 500

@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 Forbidden errors"""
    return render_template("error.html",
                         error="Access Forbidden (403)",
                         details="You don't have permission to access this resource."), 403

@app.errorhandler(401)
def unauthorized_error(error):
    """Handle 401 Unauthorized errors"""
    return render_template("error.html",
                         error="Unauthorized (401)",
                         details="Please log in to access this resource."), 401

@app.errorhandler(400)
def bad_request_error(error):
    """Handle 400 Bad Request errors"""
    return render_template("error.html",
                         error="Bad Request (400)",
                         details="The request was invalid. Please check your input and try again."), 400

@app.errorhandler(405)
def method_not_allowed_error(error):
    """Handle 405 Method Not Allowed errors"""
    return render_template("error.html",
                         error="Method Not Allowed (405)",
                         details=f"The {request.method} method is not allowed for this endpoint."), 405

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions (except HTTPExceptions which Flask handles)"""
    # Don't handle HTTPExceptions - let Flask handle those
    if isinstance(error, HTTPException):
        return error
    
    # Log the error with full traceback
    app.logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
    
    # In production, don't show full error details to users
    show_details = os.getenv("FLASK_ENV", "production") == "development"
    
    error_message = "An unexpected error occurred"
    error_details = str(error) if show_details else "Please try again later. If the problem persists, contact support at helpdesk@obis.org."
    
    return render_template("error.html",
                         error=error_message,
                         details=error_details), 500

@app.route("/token_status/admin")
def token_status_admin():
    """
    Admin-only route for system-wide token statistics.
    Only accessible if ADMIN_TOKEN_STATUS is enabled in environment.
    """
    # Check if admin endpoint is enabled
    if not os.getenv("ADMIN_TOKEN_STATUS", "").lower() == "true":
        return jsonify({
            "error": "Admin token status endpoint is disabled"
        }), 403
    
    # Require authentication
    if not github.authorized:
        return jsonify({
            "authorized": False,
            "message": "Not authorized. Please log in."
        }), 401
    
    # Optional: Check if user is admin (you can add admin user list check here)
    # admin_users = os.getenv("ADMIN_USERS", "").split(",")
    # user = session.get("user", {}).get("login", "")
    # if admin_users and user not in admin_users:
    #     return jsonify({"error": "Admin access required"}), 403
    
    # Simple token check - no validation needed
    token, redirect_response = get_token_or_redirect(github, session)
    is_valid = token is not None
    
    # Return system-wide stats (sanitized)
    return jsonify({
        "authorized": is_valid,
        "token_valid": is_valid,
        "stats": {
            "tokens_created": _token_stats['tokens_created'],
            "tokens_validated": _token_stats['tokens_validated'],
            "tokens_failed": _token_stats['tokens_failed'],
            "unique_tokens_used": len(_token_stats['token_usage_count']),
            # Don't expose token previews or usage breakdown - too sensitive
            # "token_usage_breakdown": dict(list(_token_stats['token_usage_count'].items())[:10])
        },
        "last_token_created": _token_stats['last_token_created']
    })



if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)  # , ssl_context=("server.crt", "server.key"))

