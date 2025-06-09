#!/usr/bin/env python3
"""
Simple test server for ELK composable testing
"""

from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/timeline')
def timeline():
    """Return simple test data"""
    return jsonify([
        {
            "id": "test_1",
            "content": "Test recommendation 1",
            "account": {
                "id": "1",
                "username": "testuser",
                "display_name": "Test User",
                "avatar": "https://via.placeholder.com/150"
            },
            "created_at": "2025-06-08T20:00:00Z",
            "is_recommendation": True
        },
        {
            "id": "test_2", 
            "content": "Test recommendation 2",
            "account": {
                "id": "2",
                "username": "testuser2",
                "display_name": "Test User 2",
                "avatar": "https://via.placeholder.com/150"
            },
            "created_at": "2025-06-08T20:01:00Z",
            "is_recommendation": True
        }
    ])

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    print("🧪 Starting Simple Test Server...")
    print("    Timeline: http://localhost:5004/timeline")
    print("    Health: http://localhost:5004/health")
    app.run(host='0.0.0.0', port=5004, debug=True) 