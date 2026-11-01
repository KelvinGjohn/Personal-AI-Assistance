"""
Entry point. Start the app with:

    python run.py

then open http://127.0.0.1:5000 in your browser.
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
