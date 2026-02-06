import sys
import os
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from agents.agent_reviewer import ReviewerAgent

# Configure logging
logging.basicConfig(level=logging.INFO)

SAMPLE_CODE = """
import os
import psycopg2
from flask import Flask, request, jsonify

app = Flask(__name__)

DB_HOST = "localhost"
DB_USER = "admin"
DB_PASS = "secret123" # Hardcoded secret

@app.route('/users', methods=['POST'])
def create_user():
    data = request.json
    username = data['username']
    email = data['email']

    # Direct connection in route - bad for connection pooling
    conn = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname="users_db")
    cur = conn.cursor()

    # Potential SQL Injection if not handled by library (psycopg2 handles %s usually, but context matters)
    query = "INSERT INTO users (username, email) VALUES ('%s', '%s')" % (username, email)
    cur.execute(query)

    conn.commit()
    conn.close()

    return jsonify({"status": "success"}), 201

if __name__ == '__main__':
    app.run(debug=True)
"""

REQUIREMENTS = "Create a scalable API endpoint for user registration. Ensure security and reliability standards."


def test_reviewer():
    print("Initializing Reviewer Agent...")
    try:
        agent = ReviewerAgent(model_type="code", repo_path=".")

        print("\n--- Code Under Review ---")
        print(SAMPLE_CODE.strip())
        print("-------------------------\n")

        print("Running Review...")
        review = agent.review_code(
            code=SAMPLE_CODE,
            requirements=REQUIREMENTS,
            file_path="src/api/users.py",  # Simulating a file path
        )

        print("\n--- Review Output ---")
        print(review)
        print("---------------------")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_reviewer()
