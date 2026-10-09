# Copy this file to config/local_settings.py and fill in your values.
# local_settings.py overrides config/settings.py and must NOT be uploaded to GitHub.

# DEBUG = False
# SECRET_KEY = "put-a-long-random-string-here"
# ALLOWED_HOSTS = ["your-site.onrender.com"]

JUDGE_BACKEND = "judge0"

# Option A: your own Judge0 server
# JUDGE0_URL = "http://YOUR_SERVER_IP:2358"
# JUDGE0_HEADERS = {"X-Auth-Token": "your-token"}      # only if you enabled authentication

# Option B: Judge0 CE on RapidAPI
# JUDGE0_URL = "https://judge0-ce.p.rapidapi.com"
# JUDGE0_HEADERS = {"X-RapidAPI-Key": "your-key", "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com"}

# Option C: another hosted Judge0 (for example Sulu): use the URL and header names shown in its dashboard.

# Language ids differ between Judge0 versions. Open <JUDGE0_URL>/languages and copy the ids
# of a C (GCC) entry and a Python 3 entry.
JUDGE0_LANGUAGE_IDS = {"c": 50, "python": 71}
