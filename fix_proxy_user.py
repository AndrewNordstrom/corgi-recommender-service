#!/usr/bin/env python3
"""
Script to fix the special proxy server to use the actual user ID.
"""

import os
import re
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('proxy_fixer')

def fix_proxy_verify_credentials():
    """Fix the verify_credentials function in special_proxy.py to use the actual user ID."""
    proxy_file = os.path.join(os.path.dirname(__file__), 'special_proxy.py')
    
    try:
        # Read the file
        with open(proxy_file, 'r') as f:
            content = f.read()
        
        # Define the pattern to look for
        pattern = r'@app\.route\(\'/api/v1/accounts/verify_credentials\', methods=\[\'GET\'\]\)\s*def verify_account_credentials\(\):[^}]+\s+return jsonify\(\{\s+"id": user_id,\s+"username": "demo_user",[^}]+\}\)'
        
        # Define the replacement (fixed escaping)
        replacement = '''@app.route('/api/v1/accounts/verify_credentials', methods=['GET'])
def verify_account_credentials():
    """
    Verify account credentials for Elk.
    """
    user_id = get_authenticated_user(request)
    if not user_id:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Use the actual user ID for all fields
    return jsonify({
        "id": user_id,
        "username": user_id,
        "acct": f"{user_id}@mastodon.social",
        "display_name": user_id,
        "locked": False,
        "bot": False,
        "created_at": "2023-01-01T00:00:00.000Z",
        "note": f"Corgi user: {user_id}",
        "url": f"https://mastodon.social/@{user_id}",
        "avatar": "https://mastodon.social/avatars/original/missing.png",
        "avatar_static": "https://mastodon.social/avatars/original/missing.png",
        "header": "https://mastodon.social/headers/original/missing.png",
        "header_static": "https://mastodon.social/headers/original/missing.png",
        "followers_count": 0,
        "following_count": 0,
        "statuses_count": 0,
        "source": {
            "privacy": "public",
            "sensitive": False,
            "language": "en"
        }
    })'''
        
        # Make the replacement
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        # Check if the replacement worked
        if new_content == content:
            logger.error("Failed to find the pattern to replace.")
            return False
        
        # Write the modified content back to the file
        with open(proxy_file, 'w') as f:
            f.write(new_content)
            
        logger.info("Successfully updated special_proxy.py to use actual user ID.")
        
        # Also fix the home timeline function to include a recommendation
        pattern2 = r'def get_home_timeline\(\):[\s\S]+?# Create a dummy recommendation for testing[\s\S]+?recommendation = \{[\s\S]+?\}'
        
        replacement2 = '''def get_home_timeline():
    """
    Get a user's home timeline with recommendations
    """
    request_id = hash(f"{request.remote_addr}_{request.path}") % 10000000
    
    # Get authentication
    user_id = get_authenticated_user(request)
    if not user_id:
        logger.warning(f"REQ-{request_id} | No user authenticated for timeline request")
        return jsonify([])
    
    # Get instance
    instance_url = get_user_instance(request)
    
    # Log the timeline request
    logger.info(
        f"TIMELINE-{request_id} | Requesting home timeline | "
        f"User: {user_id} | "
        f"Instance: {instance_url}"
    )
    
    try:
        # Forward request to Mastodon
        headers = {key: value for key, value in request.headers.items()
                  if key.lower() not in ['host', 'content-length']}
        params = request.args.to_dict()
        
        # Build the target URL
        target_url = urljoin(instance_url, "/api/v1/timelines/home")
        
        # Make the request
        proxied_response = requests.get(
            url=target_url,
            headers=headers,
            params=params,
            timeout=10
        )
        
        # Handle successful response
        if proxied_response.status_code == 200:
            try:
                timeline_data = proxied_response.json()
                
                # Add custom fields for testing
                for post in timeline_data:
                    post['is_real_mastodon_post'] = True
                
                # Create a dummy recommendation for testing - using the actual user ID
                recommendation = {
                    "id": f"corgi_rec_{hash(user_id) % 10000}",
                    "created_at": "2025-04-21T02:49:00.000Z",
                    "content": f"This is a test recommendation from Corgi for user {user_id}. If you see this, the proxy is working correctly with your actual account!",
                    "account": {
                        "id": "corgi",
                        "username": "corgi",
                        "display_name": "Corgi Recommender",
                        "url": "https://corgi-recommender.example.com"
                    },
                    "is_recommendation": True,
                    "is_real_mastodon_post": False,
                    "recommendation_reason": f"Testing Corgi integration with Elk for {user_id}"
                }'''
                
        # Make the replacement for the timeline function
        new_content = re.sub(pattern2, replacement2, new_content, flags=re.DOTALL)
        
        # Check if the replacement worked
        if new_content == content:
            logger.warning("Failed to find the timeline pattern to replace.")
        else:
            logger.info("Successfully updated home timeline function.")
        
        # Write the modified content back to the file
        with open(proxy_file, 'w') as f:
            f.write(new_content)
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating special_proxy.py: {e}")
        return False

if __name__ == "__main__":
    print("Fixing special_proxy.py to use the actual user ID...")
    success = fix_proxy_verify_credentials()
    
    if success:
        print("\nSuccessfully updated special_proxy.py!")
        print("Please restart the special proxy server:")
        print("1. pkill -f 'python3 special_proxy.py'")
        print("2. python3 special_proxy.py")
    else:
        print("\nFailed to update special_proxy.py. Please check the logs.")
        print("You may need to edit the file manually to fix the user ID issue.")