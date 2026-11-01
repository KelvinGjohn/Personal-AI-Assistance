# Development Environment Setup (Windows)

## 1. Install the tools

| Tool | Where to get it | Check it works |
|------|-----------------|----------------|
| Python 3.10+ | python.org (tick "Add python.exe to PATH") | `py --version` |
| Git | git-scm.com | `git --version` |
| Visual Studio Code | code.visualstudio.com | open VS Code |

> **Tip:** Keep the project in a **short path** such as `C:\Users\<you>\Desktop\JOHN`. Windows has a 260-character path limit, and some library files inside `venv` fail to load from very deep folders ("The filename or extension is too long").

## 2. Recommended VS Code extensions

- **Python** (Microsoft) — running, debugging, choosing the interpreter
- **Pylance** — autocompletion and type hints
- **Jinja** — highlighting for Flask templates
- **Markdown Preview Mermaid Support** — shows the diagrams in `documentation/`
- **GitLens** (optional) — see commit history inline

After creating the virtual environment, press `Ctrl+Shift+P` → *Python: Select Interpreter* → choose `.\venv\Scripts\python.exe`.

## 3. Create the virtual environment and install libraries

Run these in the project folder (PowerShell):

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks `Activate.ps1`, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

**Why a virtual environment?** It keeps this project's library versions separate from other Python projects on your computer, and `requirements.txt` lets anyone recreate exactly the same setup.

## 4. Create your .env file

```powershell
Copy-Item .env.example .env
py -c "import secrets; print(secrets.token_hex(32))"
```

Paste the printed value as `SECRET_KEY` in `.env`. Never commit `.env`; it is already in `.gitignore`.

## 5. Verify the environment

```powershell
python scripts/check_environment.py
python -m pytest
```

Expected: every line shows `[OK]`, then `Environment is ready.`, and pytest reports all tests passed.

## 6. Git and GitHub

```powershell
git remote add origin https://github.com/KelvinGjohn/Personal_AI_Assistant.git
git push -u origin main
```
