"""
Check the AI setup from the command line, using the settings in .env.

    python scripts/check_ai.py "What is Flask?"

With a real provider configured, this sends the message and costs a small
amount of money. In fallback mode nothing leaves this computer.
"""

import sys
from pathlib import Path

# Lets this script import the "app" package from the project folder
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.services.ai_service import AIServiceError, ask_ai  # noqa: E402

if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "Say hello in one short sentence."

    with create_app().app_context():
        try:
            response = ask_ai([{"role": "user", "content": question}])
        except AIServiceError as error:
            sys.exit(f"AI error: {error}")

    print(f"Provider: {response.provider}")
    print(f"Real AI:  {'no' if response.is_fallback else 'yes'}")
    print(response.text)
