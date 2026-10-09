# RJudge (Django)

## First-time setup (Windows, macOS or Linux)
1. Install Python 3.10+ and, for C problems, GCC (Windows: MinGW-w64 or WSL; make sure `gcc --version` works).
2. In this folder:
       python -m venv venv
       venv\Scripts\activate          (macOS/Linux: source venv/bin/activate)
       pip install -r requirements.txt
       python manage.py migrate
       python manage.py createsuperuser
       python manage.py seed_problems      (optional: adds 4 example problems)
       python manage.py runserver
3. Open http://127.0.0.1:8000/ for the site and http://127.0.0.1:8000/admin/ for the admin panel.

## Run the tests
       python manage.py test

## Adding problems (admin)
Admin > Problems > Add. Fill the statement and formats, add test cases at the bottom
(tick "Hidden" for secret ones), tick "Is published", save.

## Important
problems/judge.py runs student code directly on this computer. Use it only on your own
machine. Before a public deployment, replace evaluate() with a sandboxed judge (Judge0).

## Connecting Judge0 (sandboxed judging)
1. Copy config/local_settings.example.py to config/local_settings.py and fill in JUDGE0_URL,
   JUDGE0_HEADERS and JUDGE0_LANGUAGE_IDS (open <JUDGE0_URL>/languages for the real ids).
2. python manage.py check_judge     (must print OK for all six checks)
3. python manage.py test            (Judge0 logic is tested against a fake server, no internet needed)
4. python manage.py runserver, then submit real programs through the website.
To go back to local judging, delete local_settings.py (or set JUDGE_BACKEND = "local").
