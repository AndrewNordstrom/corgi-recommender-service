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
    
    # Generate realistic usernames and content
    realistic_users = [
        ("alex_dev", "Alex Chen", "Just shipped a new feature using #TypeScript and loving the developer experience! 🚀"),
        ("sarah_science", "Dr. Sarah Kim", "Fascinating research on machine learning bias published today. The implications for AI fairness are huge. 🧠"),
        ("mike_photos", "Mike Rodriguez", "Golden hour at the beach never gets old. Sometimes you just need to disconnect and appreciate nature 📸 #photography"),
        ("emma_writes", "Emma Thompson", "Working on my next novel and coffee consumption has reached dangerous levels ☕ Any other #writers feeling this pain?"),
        ("david_cooks", "David Park", "Trying a new recipe for Korean BBQ tacos tonight. Fusion food is where innovation happens! 🌮 #cooking"),
        ("lisa_travels", "Lisa Anderson", "Just landed in Tokyo! The energy here is incredible. First stop: authentic ramen 🍜 #travel #japan"),
        ("tom_fitness", "Tom Wilson", "5AM workout complete ✅ There's something magical about having the gym to yourself. #fitness #morningmotivation"),
        ("anna_design", "Anna Garcia", "Spent all day perfecting this color palette. Sometimes the smallest details make the biggest difference 🎨 #design"),
        ("chris_music", "Chris Taylor", "New album drops Friday! Been working on this for 2 years and can't wait to share it with the world 🎵"),
        ("ruby_tech", "Ruby Patel", "Open source contributions are up 300% this year. The community spirit in tech is amazing 💻 #opensource"),
        ("james_coffee", "James Brown", "Roasting beans at 6AM. The aroma of fresh coffee is pure magic ☕ #specialty #coffee"),
        ("zoe_startup", "Zoe Chang", "Pitch deck review at 2PM. Nervous but excited to share our vision with investors 💼 #startup #entrepreneur")
    ]
    
    # Pick a random user for variety
    user_info = realistic_users[hash(post_id) % len(realistic_users)]
    username, display_name, content = user_info
    
    return {
        'id': post_id,
        'uri': f'https://example.com/posts/{post_id}',
        'url': f'https://example.com/posts/{post_id}',
        'account': {
            'id': str(author_id),
            'username': username,
            'acct': f"{username}@example.com",
            'display_name': display_name,
            'avatar': f'https://avatar.oxro.io/avatar.svg?name={display_name.replace(" ", "%20")}&background=random',
            'avatar_static': f'https://avatar.oxro.io/avatar.svg?name={display_name.replace(" ", "%20")}&background=random',
            'header': f'https://via.placeholder.com/1500x500/cccccc/969696?text=Header',
            'header_static': f'https://via.placeholder.com/1500x500/cccccc/969696?text=Header',
            'url': f'https://example.com/@{username}',
            'note': f'Demo account showcasing Corgi AI recommendations.',
            'followers_count': hash(author_id) % 1000,
            'following_count': hash(author_id) % 500,
            'statuses_count': hash(author_id) % 2000,
            'locked': False,
            'bot': True,
            'discoverable': True,
            'created_at': '2023-01-01T00:00:00.000Z',
            'last_status_at': datetime.now().isoformat()[:10],
            'emojis': [],
            'fields': []
        },
        'content': content if rec.get('content') == 'Stub post content' else rec.get('content', content),
        'created_at': rec.get('created_at', datetime.now().isoformat() + 'Z'),
        'edited_at': None,
        'reblog': None,
        'media_attachments': rec.get('media_attachments', []),
        'mentions': [],
        'tags': [],
        'emojis': [],
        'replies_count': rec.get('replies_count', hash(post_id) % 8),
        'reblogs_count': rec.get('reblogs_count', hash(post_id) % 15),
        'favourites_count': rec.get('favourites_count', 20 + (hash(post_id) % 80)),
        # Add camelCase versions for ELK compatibility
        'repliesCount': rec.get('replies_count', hash(post_id) % 8),
        'reblogsCount': rec.get('reblogs_count', hash(post_id) % 15),
        'favouritesCount': rec.get('favourites_count', 20 + (hash(post_id) % 80)),
        'favourited': rec.get('favourited', False),
        'reblogged': rec.get('reblogged', False),
        'muted': False,
        'bookmarked': False,
        'pinned': False,
        'sensitive': False,
        'spoiler_text': '',
        'visibility': 'public',
        'language': 'en',
        'in_reply_to_id': None,
        'in_reply_to_account_id': None,
        'poll': None,
        'card': None,
        'application': {
            'name': 'Corgi AI',
            'website': 'https://example.com'
        },
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
        
        # Try to call Corgi API timeline endpoint
        try:
            response = requests.get(
                f'{CORGI_API_URL}/api/v1/recommendations/timelines/recommended',
                params={'user_id': user_id, 'limit': limit},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                timeline = data if isinstance(data, list) else []
                
                if timeline:
                    # Transform to Mastodon format
                    transformed_timeline = [transform_to_mastodon_post(post) for post in timeline]
                    return jsonify(transformed_timeline)
        except requests.RequestException:
            pass  # Fall through to generate demo content
        
        # Generate demo content when Corgi API is unavailable or returns empty
        demo_posts = []
        for i in range(min(limit, 15)):  # Generate up to 15 demo posts
            demo_post = {
                'id': f'demo_post_{i}_{int(datetime.now().timestamp())}',
                'author_id': f'demo_user_{i}',
                # The transform function will pick realistic content based on the ID
            }
            demo_posts.append(transform_to_mastodon_post(demo_post))
        
        return jsonify(demo_posts)
        
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