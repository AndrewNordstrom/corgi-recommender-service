#!/usr/bin/env python3
"""
Simple test server to check connectivity
"""

from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return {'status': 'ok', 'message': 'Test server is running'}

if __name__ == '__main__':
    print("Starting test server on port 5005...")
    app.run(host='127.0.0.1', port=5005, debug=True)