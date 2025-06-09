#!/usr/bin/env python3
"""
Simple demo endpoint for ELK integration
This serves as a bridge between ELK's /corgi page and the Corgi API
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app, origins=["http://localhost:5314"], methods=["GET", "POST", "OPTIONS"])

CORGI_API_URL = 'http://localhost:9999'

def transform_to_mastodon_post(rec):
    """Transform stub post to full Mastodon-compatible format"""
    
    # If it's already a full Mastodon post, just add recommendation metadata
    if isinstance(rec, dict) and rec.get('account', {}).get('username'):
        rec['is_recommendation'] = True
        rec['recommendation_reason'] = rec.get('recommendation_reason') or rec.get('reason') or 'AI recommended based on your interests'
        return rec

    # If it's a stub post, create a full Mastodon-compatible structure
    post_id = rec.get('id', f"rec_{int(datetime.now().timestamp())}")
    author_id = rec.get('author_id', f"user_{hash(post_id) % 1000}")
    author_name = rec.get('author_name', f"User {str(author_id)[-4:]}")
    
    return {
        'id': post_id,
        'uri': f'https://example.com/posts/{post_id}',
        'url': f'https://example.com/posts/{post_id}',
        'account': {
            'id': str(author_id),
            'username': author_name.lower().replace(' ', ''),
            'acct': f"{author_name.lower().replace(' ', '')}@example.com",
            'display_name': author_name,
            'avatar': f'https://avatar.oxro.io/avatar.svg?name={author_name.replace(" ", "%20")}&background=random',
            'url': f'https://example.com/@{author_name.lower().replace(" ", "")}'
        },
        'content': rec.get('content', 'AI-generated recommendation content'),
        'created_at': rec.get('created_at', datetime.now().isoformat() + 'Z'),
        'reblog': None,
        'media_attachments': rec.get('media_attachments', []),
        'replies_count': rec.get('replies_count', 0),
        'reblogs_count': rec.get('reblogs_count', 0),
        'favourites_count': rec.get('favourites_count', 0),
        'favourited': rec.get('favourited', False),
        'reblogged': rec.get('reblogged', False),
        'is_recommendation': True,
        'recommendation_reason': rec.get('recommendation_reason') or rec.get('reason') or 'AI recommended based on your interests'
    }

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Check if Corgi API is accessible
        response = requests.get(f'{CORGI_API_URL}/health', timeout=5)
        corgi_healthy = response.status_code == 200
        
        return jsonify({
            'status': 'healthy' if corgi_healthy else 'degraded',
            'corgi_api': 'connected' if corgi_healthy else 'disconnected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/recommendations')
def get_recommendations():
    """Get recommendations in Mastodon-compatible format"""
    try:
        # Get parameters
        user_id = request.args.get('user_id', 'demo_user')
        limit = int(request.args.get('limit', '10'))
        
        # Call Corgi API
        response = requests.get(
            f'{CORGI_API_URL}/api/v1/recommendations',
            params={'user_id': user_id, 'limit': limit},
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({
                'error': f'Corgi API returned {response.status_code}',
                'message': 'Failed to fetch recommendations'
            }), response.status_code
        
        data = response.json()
        
        # Extract recommendations
        recs = data.get('recommendations', [])
        if not recs:
            return jsonify([])  # Return empty array for ELK compatibility
        
        # Transform to Mastodon format
        transformed_recs = [transform_to_mastodon_post(rec) for rec in recs]
        
        return jsonify(transformed_recs)
        
    except requests.RequestException as e:
        return jsonify({
            'error': 'Connection to Corgi API failed',
            'details': str(e)
        }), 503
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/timeline', methods=['GET', 'OPTIONS'])
def get_timeline():
    """Get timeline with recommendations in Mastodon-compatible format"""
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        # Get parameters
        user_id = request.args.get('user_id', 'demo_user')
        limit = int(request.args.get('limit', '20'))
        
        # Call Corgi API timeline endpoint
        response = requests.get(
            f'{CORGI_API_URL}/api/v1/recommendations/timelines/recommended',
            params={'user_id': user_id, 'limit': limit},
            timeout=10
        )
        
        if response.status_code != 200:
            return jsonify({
                'error': f'Corgi API returned {response.status_code}',
                'message': 'Failed to fetch timeline'
            }), response.status_code
        
        data = response.json()
        
        # Ensure we have an array
        timeline = data if isinstance(data, list) else []
        
        if not timeline:
            return jsonify([])  # Return empty array for ELK compatibility
        
        # Transform to Mastodon format
        transformed_timeline = [transform_to_mastodon_post(post) for post in timeline]
        
        return jsonify(transformed_timeline)
        
    except requests.RequestException as e:
        return jsonify({
            'error': 'Connection to Corgi API failed',
            'details': str(e)
        }), 503
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500

@app.route('/demo')
def demo_page():
    """Simple demo page showing integration status"""
    try:
        # Check Corgi API health
        health_response = requests.get(f'{CORGI_API_URL}/health', timeout=5)
        api_status = "✅ Connected" if health_response.status_code == 200 else "❌ Disconnected"
        
        # Get sample recommendations
        recs_response = requests.get(
            f'{CORGI_API_URL}/api/v1/recommendations',
            params={'user_id': 'demo_user', 'limit': 3},
            timeout=5
        )
        
        recs_count = 0
        if recs_response.status_code == 200:
            recs_data = recs_response.json()
            recs_count = len(recs_data.get('recommendations', []))
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Corgi ELK Integration Demo</title>
            <style>
                body {{ font-family: system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }}
                .status {{ padding: 20px; background: #f5f5f5; border-radius: 8px; margin: 20px 0; }}
                .success {{ background: #e8f5e8; }}
                .error {{ background: #ffe8e8; }}
                code {{ background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <h1>🐕 Corgi ELK Integration</h1>
            
            <div class="status success">
                <h3>Integration Status</h3>
                <p><strong>Corgi API:</strong> {api_status}</p>
                <p><strong>Recommendations Available:</strong> {recs_count}</p>
                <p><strong>Demo Endpoint:</strong> ✅ Running on port 5001</p>
            </div>
            
            <h3>Available Endpoints</h3>
            <ul>
                <li><code>GET /recommendations?user_id=demo_user&limit=10</code> - Get recommendations</li>
                <li><code>GET /timeline?user_id=demo_user&limit=20</code> - Get timeline with recommendations</li>
                <li><code>GET /health</code> - Health check</li>
            </ul>
            
            <h3>Testing</h3>
            <p>Test the endpoints:</p>
            <ul>
                <li><a href="/recommendations?user_id=demo_user&limit=5">Sample Recommendations</a></li>
                <li><a href="/timeline?user_id=demo_user&limit=5">Sample Timeline</a></li>
                <li><a href="/health">Health Check</a></li>
            </ul>
            
            <p><em>This demo bridge makes Corgi recommendations accessible to ELK in Mastodon-compatible format.</em></p>
        </body>
        </html>
        """
        
        return html
        
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

if __name__ == '__main__':
    print("🐕 Starting Corgi ELK Demo Bridge...")
    port = int(os.environ.get('PORT', 5003))
    print(f"    Demo page: http://localhost:{port}/demo")
    print(f"    Recommendations: http://localhost:{port}/recommendations?user_id=demo_user")
    print(f"    Timeline: http://localhost:{port}/timeline?user_id=demo_user")
    app.run(host='0.0.0.0', port=port, debug=True) 