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
import io
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
from dois import ObisDoi
from convert_to_dwc import convert_to_dwc as run_dwc_conversion

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

@app.route("/admin/bioeco-owners", methods=["GET", "POST"])
def manage_bioeco_owners():
    """Admin endpoint to manage BioEco entry ownership."""
    user = get_or_fetch_user(github, session)
    
    # Only allow admin users to access this page
    if not user or not is_admin(user, ADMIN_USERS):
        return redirect(url_for('index'))
    
    if request.method == "GET":
        # Load current bioeco owner mappings
        bioeco_owners = {}
        try:
            with open("bioeco_creators.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                bioeco_owners = data.get("creators", {})
        except Exception as e:
            print(f"Error loading bioeco creators: {e}")
        
        # Load all programs from program_names.txt
        bioeco_entries = []
        try:
            with open("program_names.txt", "r", encoding="utf-8") as f:
                programs = [line.strip() for line in f if line.strip()]
            
            for i, program_name in enumerate(programs):
                entry_id = f"bioeco-{i}"
                bioeco_entries.append({
                    "id": entry_id,
                    "index": i,
                    "name": program_name,
                    "owner": bioeco_owners.get(entry_id, None)
                })
        except Exception as e:
            print(f"Error loading bioeco entries from program_names.txt: {e}")
        
        return render_template("admin/bioeco_owners.html", entries=bioeco_entries)
    
    elif request.method == "POST":
        # Update bioeco owner
        entry_id = request.form.get("entry_id")
        new_owner = request.form.get("new_owner")
        
        if not entry_id:
            return jsonify({"success": False, "error": "Entry ID required"}), 400
        
        try:
            # Load current data
            bioeco_owners = {}
            try:
                with open("bioeco_creators.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    bioeco_owners = data.get("creators", {})
            except FileNotFoundError:
                bioeco_owners = {}
            
            # Update or remove owner
            if new_owner and new_owner.strip():
                bioeco_owners[entry_id] = new_owner.strip()
            else:
                bioeco_owners[entry_id] = None
            
            # Save updated data
            with open("bioeco_creators.json", "w", encoding="utf-8") as f:
                json.dump({
                    "notes": "This file maps BioEco entry IDs to their creators (GitHub usernames).",
                    "creators": bioeco_owners
                }, f, indent=2)
            
            return jsonify({"success": True, "message": f"Owner updated for {entry_id}"}), 200
        except Exception as e:
            print(f"Error updating bioeco owner: {e}")
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
    # Get the form data (action)
    action = request.form.get("action")
    output = makeFormJson()  # Returns single @graph output
    print("attempting to get issue number")
    print("session issue number: ", session.get('issue_number', 'N/A'))
    
    # Call the function to process the action, passing the output object
    # github_request wrapper will handle token and 401 errors automatically
    result = process_submission_action(
        session.get('issue_number', None), 
        action, 
        output,
        GITHUB_API_URL, REPO_OWNER, GITHUB_REPO,
        github, session)
    print("ACTION RESULT: ", result)
    
    # Handle print_json action
    if action == "print_json":
        return render_template("print_json.html", 
        output=json.dumps(output, indent=4))

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

    # Load bioeco entries with access control
    user = session.get("user")
    bioeco_entries = load_bioeco_entries_with_access_control(user, ADMIN_USERS)

    # Combine GitHub issues and bioeco entries
    all_entries = filtered_issues + bioeco_entries

    if request.method == "GET":
        return render_template("update_entry.html", issues=all_entries, admin_users=ADMIN_USERS)

    elif request.method == "POST":
        print(request.get_data())
        # Fetch the selected issue
        print(str(request))
        print('setting default value')
        print("session issue number after setting default value: ", session.get('issue_number', 'N/A'))
        issue_number = request.form.get("selected_issue", 'N/A')
        if issue_number:
            # Check if it's a bioeco entry
            if issue_number.startswith("bioeco-"):
                # Handle bioeco entry - find the folder name from the entry
                try:
                    # Find the entry in all_entries to get the folder name
                    bioeco_entry = None
                    for entry in all_entries:
                        if entry.get("number") == issue_number and entry.get("is_bioeco"):
                            bioeco_entry = entry
                            break
                    
                    if not bioeco_entry:
                        return redirect_to_error("BioEco entry not found")
                    
                    folder = bioeco_entry.get("folder")
                    if not folder:
                        return redirect_to_error("Invalid BioEco entry", "No folder information")
                    
                    # Fetch the BioEco JSON using the API endpoint
                    # This abstracts away the GitHub URL construction
                    json_url = f"https://raw.githubusercontent.com/BioEcoOcean/metadata-tracking-dev/main/jsonFiles/{folder}/{folder}.json"
                    json_resp = requests.get(json_url, timeout=10)
                    if json_resp.status_code != 200:
                        return redirect_to_error("Failed to fetch BioEco data", f"Could not load {folder}.json")
                    
                    json_data = json_resp.json()
                    if isinstance(json_data, dict) and "@graph" in json_data:
                        output_data = json_data
                    elif isinstance(json_data, list):
                        output_data = {"@graph": json_data}
                    else:
                        output_data = {"@graph": [json_data]}
                    
                    # Store folder info in session for later use
                    session['bioeco_folder'] = folder
                    session['issue_number'] = issue_number
                    
                    # Process like regular entry
                    project_node, action_node, frequency_node = split_metadata_submission_graph(output_data)
                    project_node = strip_schema_org_prefixes(project_node) if project_node else {}
                    action_node = strip_schema_org_prefixes(action_node) if action_node else {}
                    frequency_node = strip_schema_org_prefixes(frequency_node) if frequency_node else {}
                    mapped_schema_entry = map_form_to_schema(project_node, schema_field_mapping)
                    mapped_actions = map_form_to_schema(action_node, actions_field_mapping)
                    mapped_frequency = map_form_to_schema(frequency_node, frequency_field_mapping)
                    form_html = generate_form(
                        prefilled_data=mapped_schema_entry,
                        actions_data=mapped_actions,
                        frequency_data=mapped_frequency,
                    )
                    
                    return render_template("update_entry.html", issues=all_entries, form_html=form_html, issue_number=issue_number, admin_users=ADMIN_USERS)
                except Exception as e:
                    print(f"Error loading BioEco entry: {e}")
                    return redirect_to_error("Error loading BioEco entry", str(e))
            else:
                # Handle regular GitHub issue
                print("issue number: ", issue_number, "type: ", type(issue_number), "request: ", request.method)
                session['issue_number'] = issue_number
                print("session issue number after setting it with real value: ", session.get('issue_number', 'N/A'))
                issue_url = f"https://api.github.com/repos/{REPO_OWNER}/{GITHUB_REPO}/issues/{issue_number}"
                # Use github_request wrapper - handles token and 401 automatically
                response, redirect_response = github_request(github, session, "get", issue_url, timeout=10)
                if redirect_response:
                    return redirect_response
                
                response_data = response.json()  # Debug: Inspect the full response from GitHub
                print(f"Response Data: {response_data}")

                if response.status_code == 200:
                    # Parse the issue data
                    issue_data = response.json()
                    issue_body = issue_data["body"]
                    json_blocks = extract_json_blocks(issue_body)
                    
                    # Single combined JSON-LD: @graph has Project, Action, and frequency nodes
                    output_json = json_blocks.get("Metadata Submission")
                    if output_json:
                        output_data = (
                            json.loads(output_json)
                            if isinstance(output_json, str)
                            else output_json
                        )
                        project_node, action_node, frequency_node = split_metadata_submission_graph(output_data)
                        project_node = strip_schema_org_prefixes(project_node) if project_node else {}
                        action_node = strip_schema_org_prefixes(action_node) if action_node else {}
                        frequency_node = strip_schema_org_prefixes(frequency_node) if frequency_node else {}
                        mapped_schema_entry = map_form_to_schema(project_node, schema_field_mapping)
                        mapped_actions = map_form_to_schema(action_node, actions_field_mapping)
                        mapped_frequency = map_form_to_schema(frequency_node, frequency_field_mapping)
                        form_html = generate_form(
                            prefilled_data=mapped_schema_entry,
                            actions_data=mapped_actions,
                            frequency_data=mapped_frequency,
                        )
                    else:
                        schema_entry = json_blocks.get("Metadata Submission")
                        mapped_schema_entry = map_form_to_schema(schema_entry, schema_field_mapping) if schema_entry else {}
                        form_html = generate_form(prefilled_data=mapped_schema_entry)

                    return render_template("update_entry.html", issues=all_entries, form_html=form_html, issue_number=issue_number, admin_users=ADMIN_USERS)
        else:
            return redirect_to_error("No issue selected", "Please select an issue to update.")

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

@app.route("/api/bioeco/<folder_name>")
def fetch_bioeco_json(folder_name):
    """
    API endpoint to fetch a single BioEco JSON file.
    Called when a user selects a program from the dropdown.
    
    Args:
        folder_name: The folder name/program name to fetch
        
    Returns:
        JSON response with the fetched data or error
    """
    try:
        # Fetch the JSON file from GitHub
        json_url = f"https://raw.githubusercontent.com/BioEcoOcean/metadata-tracking-dev/main/jsonFiles/{folder_name}/{folder_name}.json"
        resp = requests.get(json_url, timeout=10)
        
        if resp.status_code != 200:
            return jsonify({"success": False, "error": f"Failed to fetch {folder_name}.json"}), 404
        
        json_data = resp.json()
        
        # Normalize the data structure (handle both wrapped and unwrapped)
        if isinstance(json_data, dict) and "@graph" in json_data:
            output_data = json_data
        elif isinstance(json_data, list):
            output_data = {"@graph": json_data}
        else:
            output_data = {"@graph": [json_data]}
        
        return jsonify({"success": True, "data": output_data, "folder": folder_name})
    except requests.Timeout:
        return jsonify({"success": False, "error": "Request timeout while fetching BioEco data"}), 408
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

