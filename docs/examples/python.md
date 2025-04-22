# Python Client Example

This guide demonstrates how to integrate Corgi with a Python application using the `requests` library. We'll create a simple script that fetches personalized recommendations and logs user interactions.

## Prerequisites

- Python 3.6+
- `requests` library (`pip install requests`)
- A Corgi API key
- A user ID in your Corgi system

## Basic Client

Let's start with a simple client class that handles authentication and common API operations:

```python
import requests
import json

class CorgiClient:
    """
    Simple Python client for the Corgi Recommender Service API.
    """
    
    def __init__(self, api_key, base_url="https://api.corgi-recs.io"):
        """
        Initialize the client with your API key.
        
        Args:
            api_key (str): Your Corgi API key
            base_url (str): The base URL for the Corgi API
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_recommendations(self, user_id, limit=10, exclude_seen=True, languages=None, debug=False):
        """
        Get personalized recommendations for a user.
        
        Args:
            user_id (str): The user ID to get recommendations for
            limit (int): Maximum number of recommendations to return
            exclude_seen (bool): Whether to exclude posts the user has already seen
            languages (list): List of language codes to filter by (e.g., ["en", "es"])
            debug (bool): Whether to include debug information in the response
            
        Returns:
            dict: The recommendations response
        """
        params = {
            "user_id": user_id,
            "limit": limit,
            "exclude_seen": exclude_seen,
            "debug": debug
        }
        
        if languages:
            params["languages"] = ",".join(languages)
        
        response = requests.get(
            f"{self.base_url}/api/v1/recommendations",
            headers=self.headers,
            params=params
        )
        
        response.raise_for_status()
        return response.json()
    
    def log_interaction(self, user_id, post_id, action_type, context=None):
        """
        Log a user interaction with a post.
        
        Args:
            user_id (str): The user ID
            post_id (str): The post ID
            action_type (str): The type of interaction (favorite, bookmark, reblog, etc.)
            context (dict): Additional context about the interaction
            
        Returns:
            dict: The response
        """
        data = {
            "user_alias": user_id,
            "post_id": post_id,
            "action_type": action_type
        }
        
        if context:
            data["context"] = context
            
        response = requests.post(
            f"{self.base_url}/api/v1/interactions",
            headers=self.headers,
            json=data
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_privacy_settings(self, user_id):
        """
        Get privacy settings for a user.
        
        Args:
            user_id (str): The user ID
            
        Returns:
            dict: The privacy settings
        """
        response = requests.get(
            f"{self.base_url}/api/v1/privacy",
            headers=self.headers,
            params={"user_id": user_id}
        )
        
        response.raise_for_status()
        return response.json()
    
    def update_privacy_settings(self, user_id, tracking_level):
        """
        Update privacy settings for a user.
        
        Args:
            user_id (str): The user ID
            tracking_level (str): The tracking level (full, limited, or none)
            
        Returns:
            dict: The updated privacy settings
        """
        data = {
            "user_id": user_id,
            "tracking_level": tracking_level
        }
        
        response = requests.post(
            f"{self.base_url}/api/v1/privacy",
            headers=self.headers,
            json=data
        )
        
        response.raise_for_status()
        return response.json()
```

## Example Usage

Here's how to use our client to fetch recommendations and log interactions:

```python
def main():
    # Initialize the client
    api_key = "YOUR_API_KEY"
    user_id = "user_12345"
    client = CorgiClient(api_key)
    
    # Get recommendations
    print("Fetching recommendations...")
    recommendations = client.get_recommendations(
        user_id=user_id,
        limit=5,
        languages=["en"],
        debug=True
    )
    
    # Display recommendations
    print(f"Found {len(recommendations['recommendations'])} recommendations:")
    for i, post in enumerate(recommendations['recommendations'], 1):
        print(f"\n--- Recommendation {i} ---")
        print(f"Author: {post['account']['display_name']} (@{post['account']['username']})")
        
        # Strip HTML for cleaner display
        content = post['content'].replace("<p>", "").replace("</p>", "")
        print(f"Content: {content[:100]}...")
        
        print(f"Score: {post['ranking_score']:.2f}")
        print(f"Reason: {post['recommendation_reason']}")
        print(f"ID: {post['id']}")
    
    # If debug info was requested, show it
    if 'debug_info' in recommendations:
        print("\n--- Debug Info ---")
        debug = recommendations['debug_info']
        print(f"User interactions: {debug['user_interactions_count']}")
        print(f"Candidates evaluated: {debug['candidates_evaluated']}")
        print(f"Weights: {json.dumps(debug['factor_weights'], indent=2)}")
    
    # Simulate user interaction with first recommendation
    if recommendations['recommendations']:
        first_post = recommendations['recommendations'][0]
        post_id = first_post['id']
        
        print(f"\nLogging a 'favorite' interaction for post {post_id}...")
        result = client.log_interaction(
            user_id=user_id,
            post_id=post_id,
            action_type="favorite",
            context={
                "source": "python_example",
                "recommendation": True
            }
        )
        print(f"Interaction logged: {result}")
    
    # Get current privacy settings
    print("\nChecking privacy settings...")
    privacy = client.get_privacy_settings(user_id)
    print(f"Current tracking level: {privacy['tracking_level']}")

if __name__ == "__main__":
    main()
```

## Full Application Example

Let's create a more complete application that allows exploring recommendations and interacting with posts:

```python
import argparse
import json
import requests
from datetime import datetime
import html
import re

class CorgiClient:
    # (Implementation from above)
    pass

def strip_html(text):
    """Remove HTML tags from text."""
    text = re.sub(r'<[^>]+>', '', text)
    return html.unescape(text).strip()

def format_timestamp(timestamp):
    """Format ISO timestamp to a readable format."""
    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def explore_recommendations(client, user_id):
    """Interactive exploration of recommendations."""
    while True:
        print("\n=== Recommendation Explorer ===")
        print("1. Get recommendations")
        print("2. View privacy settings")
        print("3. Update privacy settings")
        print("4. Quit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == '1':
            limit = int(input("Number of recommendations (1-20): ") or "5")
            debug = input("Include debug info? (y/n): ").lower() == 'y'
            languages = input("Filter by languages (comma-separated, e.g., en,es) or leave empty: ")
            
            languages_list = None
            if languages:
                languages_list = [lang.strip() for lang in languages.split(',')]
            
            try:
                recommendations = client.get_recommendations(
                    user_id=user_id,
                    limit=limit,
                    languages=languages_list,
                    debug=debug
                )
                
                display_recommendations(client, user_id, recommendations)
                
            except requests.RequestException as e:
                print(f"Error fetching recommendations: {e}")
        
        elif choice == '2':
            try:
                privacy = client.get_privacy_settings(user_id)
                print("\n=== Privacy Settings ===")
                print(f"User ID: {privacy['user_id']}")
                print(f"Tracking level: {privacy['tracking_level']}")
                print(f"Created at: {privacy.get('created_at', 'N/A')}")
                print(f"Updated at: {privacy.get('updated_at', 'N/A')}")
            except requests.RequestException as e:
                print(f"Error fetching privacy settings: {e}")
        
        elif choice == '3':
            print("\n=== Update Privacy Settings ===")
            print("Available tracking levels:")
            print("  full - Maximum personalization (stores all interactions)")
            print("  limited - Balanced approach (stores aggregate data only)")
            print("  none - Maximum privacy (no personalization)")
            
            level = input("\nEnter new tracking level: ")
            if level in ['full', 'limited', 'none']:
                try:
                    result = client.update_privacy_settings(user_id, level)
                    print(f"Privacy settings updated to: {result['tracking_level']}")
                except requests.RequestException as e:
                    print(f"Error updating privacy settings: {e}")
            else:
                print("Invalid tracking level. Please choose from 'full', 'limited', or 'none'.")
        
        elif choice == '4':
            break
        
        else:
            print("Invalid choice. Please enter a number from 1-4.")

def display_recommendations(client, user_id, recommendations):
    """Display recommendations and allow interactions."""
    posts = recommendations['recommendations']
    
    if not posts:
        print("No recommendations found.")
        return
    
    print(f"\nFound {len(posts)} recommendations:")
    
    for i, post in enumerate(posts):
        print(f"\n--- Recommendation {i+1}/{len(posts)} ---")
        print(f"Author: {post['account']['display_name']} (@{post['account']['username']})")
        print(f"Posted: {format_timestamp(post['created_at'])}")
        print(f"Content: {strip_html(post['content'])[:150]}...")
        print(f"Reason: {post['recommendation_reason']}")
        print(f"Score: {post['ranking_score']:.2f}")
        
        actions = ['next', 'favorite', 'bookmark', 'reblog', 'skip', 'quit']
        
        while True:
            action = input(f"\nAction ({'/'.join(actions)}): ").lower()
            
            if action == 'next' or action == '':
                break
            elif action == 'skip':
                break
            elif action == 'quit':
                return
            elif action in ['favorite', 'bookmark', 'reblog']:
                try:
                    result = client.log_interaction(
                        user_id=user_id,
                        post_id=post['id'],
                        action_type=action,
                        context={
                            "source": "python_example",
                            "recommendation": True
                        }
                    )
                    print(f"Interaction logged: {result['status']}")
                except requests.RequestException as e:
                    print(f"Error logging interaction: {e}")
            else:
                print(f"Invalid action. Please choose from: {', '.join(actions)}")
    
    # If debug info was requested, show it
    if 'debug_info' in recommendations:
        print("\n=== Debug Info ===")
        debug = recommendations['debug_info']
        print(f"User interactions: {debug['user_interactions_count']}")
        print(f"Candidates evaluated: {debug['candidates_evaluated']}")
        print("Factor weights:")
        for factor, weight in debug['factor_weights'].items():
            print(f"  {factor}: {weight}")

def main():
    parser = argparse.ArgumentParser(description="Corgi Recommender Service Client")
    parser.add_argument("--api-key", required=True, help="Your Corgi API key")
    parser.add_argument("--user-id", required=True, help="User ID for recommendations")
    parser.add_argument("--base-url", default="https://api.corgi-recs.io", help="API base URL")
    
    args = parser.parse_args()
    
    client = CorgiClient(api_key=args.api_key, base_url=args.base_url)
    
    print(f"Corgi Recommender Service Client")
    print(f"Connected to: {args.base_url}")
    print(f"User ID: {args.user_id}")
    
    try:
        explore_recommendations(client, args.user_id)
    except KeyboardInterrupt:
        print("\nExiting...")

if __name__ == "__main__":
    main()
```

## Using with Jupyter Notebook

Corgi works great with Jupyter Notebooks for data analysis and visualization. Here's a simple example:

```python
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configure the client
API_KEY = "YOUR_API_KEY"
USER_ID = "user_12345"
BASE_URL = "https://api.corgi-recs.io"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Get recommendations with debug info
response = requests.get(
    f"{BASE_URL}/api/v1/recommendations",
    headers=headers,
    params={
        "user_id": USER_ID,
        "limit": 20,
        "debug": True
    }
)

data = response.json()

# Extract recommendations into a DataFrame
posts = pd.DataFrame([
    {
        'post_id': post['id'],
        'author': post['account']['display_name'],
        'score': post['ranking_score'],
        'reason': post['recommendation_reason'],
        'created_at': pd.to_datetime(post['created_at'])
    }
    for post in data['recommendations']
])

# Display the recommendations
posts

# Visualize the distribution of recommendation reasons
plt.figure(figsize=(10, 6))
reason_counts = posts['reason'].value_counts()
sns.barplot(x=reason_counts.index, y=reason_counts.values)
plt.title('Distribution of Recommendation Reasons')
plt.ylabel('Count')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Visualize the distribution of scores
plt.figure(figsize=(10, 6))
sns.histplot(posts['score'], bins=10)
plt.title('Distribution of Recommendation Scores')
plt.xlabel('Score')
plt.ylabel('Count')
plt.show()

# Plot scores by reason
plt.figure(figsize=(10, 6))
sns.boxplot(x='reason', y='score', data=posts)
plt.title('Recommendation Scores by Reason')
plt.ylabel('Score')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
```

## Integration with Web Applications

For web applications, you might want to create an API wrapper:

```python
from flask import Flask, jsonify, request
import requests

app = Flask(__name__)

CORGI_API_KEY = "YOUR_API_KEY"
CORGI_BASE_URL = "https://api.corgi-recs.io"

def get_corgi_headers():
    return {
        "Authorization": f"Bearer {CORGI_API_KEY}",
        "Content-Type": "application/json"
    }

@app.route('/recommendations')
def recommendations():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id parameter is required"}), 400
    
    limit = request.args.get('limit', default=10, type=int)
    
    # Forward request to Corgi
    response = requests.get(
        f"{CORGI_BASE_URL}/api/v1/recommendations",
        headers=get_corgi_headers(),
        params={
            "user_id": user_id,
            "limit": limit
        }
    )
    
    # Return the response to the client
    return jsonify(response.json())

@app.route('/interactions', methods=['POST'])
def log_interaction():
    data = request.json
    
    # Forward to Corgi
    response = requests.post(
        f"{CORGI_BASE_URL}/api/v1/interactions",
        headers=get_corgi_headers(),
        json=data
    )
    
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(debug=True)
```

## Next Steps

- Try building a [CLI tool](cli.md) with Corgi
- Explore [Elk integration](elk.md) for a web client example
- Learn about the [Recommendation Engine](../concepts/recommendations.md) to understand how it works