"""
Application constants and configuration.
"""
import os
import platform #for runing locally
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# GitHub Configuration
# ============================================================================
REPO_OWNER = "iobis"
GITHUB_REPO = "eov-metadata-app-front-entries"
BRANCH = "refs/heads/main"
JSON_FOLDER = "jsonFiles"
GITHUB_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{GITHUB_REPO}/issues"
GITHUB_API_JSONS = f"https://api.github.com/repos/{REPO_OWNER}/{GITHUB_REPO}/contents/{JSON_FOLDER}"
RAW_BASE_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{GITHUB_REPO}/{BRANCH}/{JSON_FOLDER}"

# ============================================================================
# Application Configuration
# ============================================================================
if platform.system() == "Windows": #this is for trying to install R, but when I was installing it locally
    R_PATH = r"C:\Program Files\R\R-4.4.2\bin\Rscript.exe"
else:
    R_PATH = "Rscript"

EOV_USER = os.getenv("EOV_USER")
EOV_PASS = os.getenv("EOV_PASS")

# ============================================================================
# Access Control Configuration
# ============================================================================
# Set the GitHub usernames of app admins (can see all entries)
# Can be a comma-separated list: "user1,user2,user3"
# You can override this via ADMIN_USERS environment variable
ADMIN_USERS = [
    username.strip() 
    for username in os.getenv("ADMIN_USERS", "EliLawrence,pieterprovoost,sformel").split(",")
    if username.strip()
]

