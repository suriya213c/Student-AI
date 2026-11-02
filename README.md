# Student AI

Student AI is a Streamlit learning app with AI-assisted tutoring, summaries, quizzes, study resources, attendance tracking, and performance tools.

## Run locally

From this directory, install the declared dependencies and start Streamlit:

```shell
python -m venv .venv
```

On Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```shell
source .venv/bin/activate
```

Then, on any platform:

```shell
python -m pip install -r requirements.txt
streamlit run app.py
```

AI features use the Gemini API. Add your own key to `.streamlit/secrets.toml` (this local secrets file is ignored by Git):

```toml
GEMINI_API_KEY = "your-key"
```

The app stores user and learning data in `eduai.db` in the current directory. Keep this database and any personal data out of source-control commits.

## Security behavior

New passwords are stored using salted PBKDF2-HMAC-SHA256 hashes. Existing SHA-256 password hashes are upgraded after a successful login. Web resources are limited to HTTP(S) URLs resolving only to public IP addresses; redirects are checked again, and connections are pinned to the validated IP.

## Tests

```shell
python -m unittest discover -s tests -v
```
