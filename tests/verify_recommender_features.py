#!/usr/bin/env python3
"""
verify_recommender_features.py

Standalone script to verify high-level architectural features of the Corgi recommender system.
- Does NOT use pytest.
- Makes real HTTP requests to the running server.
- Prints results in a human-readable format.

Features verified:
1. Personalized Recommendations & Transparent Reasoning
2. Cold Start Handling
"""
import requests
import random
import string
import time

API_BASE = "http://localhost:5002/api/v1"
INTERACTIONS_ENDPOINT = f"{API_BASE}/interactions"
TIMELINE_ENDPOINT = f"{API_BASE}/recommendations/timeline"

# Utility to generate a random user_id

def random_user_id(prefix="user"):
    return f"{prefix}_" + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))

def print_recommendations(title, recs):
    print(f"\n=== {title} ===")
    for i, post in enumerate(recs[:5], 1):
        author = post.get("account", {}).get("username") or post.get("author_id")
        score = post.get("ranking_score")
        reason = post.get("recommendation_reason") or post.get("reason_detail")
        print(f"#{i}: Author: {author} | Score: {score} | Reason: {reason}")
    print()

def simulate_interactions(user_id, post_ids_by_author):
    """
    Simulate user interactions: likes for posts from each author.
    post_ids_by_author: dict of {author: [post_id, ...]}
    """
    for author, post_ids in post_ids_by_author.items():
        for post_id in post_ids:
            payload = {
                "user_id": user_id,
                "post_id": post_id,
                "interaction_type": "favorite"
            }
            r = requests.post(INTERACTIONS_ENDPOINT, json=payload)
            if r.status_code != 200:
                print(f"[WARN] Failed to record interaction for {user_id} on {post_id}: {r.text}")
            time.sleep(0.1)  # avoid hammering the API

def fetch_timeline(user_id):
    params = {"user_id": user_id, "limit": 10, "fetch_real_time": "false"}
    r = requests.get(TIMELINE_ENDPOINT, params=params)
    if r.status_code != 200:
        print(f"[ERROR] Timeline fetch failed for {user_id}: {r.text}")
        return []
    return r.json()

def main():
    print("Verifying Corgi Recommender System Features\n")
    # 1. Personalized Recommendations & Transparent Reasoning
    user_personal = random_user_id("personalized")
    print(f"[INFO] Using test user_id for personalization: {user_personal}")

    # Discover available posts and authors
    timeline = fetch_timeline("anonymous")
    authors = {}
    for post in timeline:
        author = post.get("account", {}).get("username") or post.get("author_id")
        if author not in authors:
            authors[author] = []
        authors[author].append(post.get("id") or post.get("post_id"))
    # Sort authors by post count (desc)
    author_list = sorted(authors.keys(), key=lambda a: len(authors[a]), reverse=True)

    if len(author_list) < 2:
        print("[WARN] Less than two authors detected – personalization test may be limited.")

    author_a = author_list[0]
    author_b = author_list[1] if len(author_list) > 1 else author_list[0]

    # Ensure we have enough posts to simulate 3 vs 1 interactions
    posts_a = authors[author_a][: min(3, len(authors[author_a]))]
    posts_b = authors[author_b][:1] if author_b != author_a else []

    if not posts_b:
        print("[WARN] Only one distinct author available; skipping comparative personalization test.")
        posts_b = []

    interaction_plan = {author_a: posts_a}
    if posts_b:
        interaction_plan[author_b] = posts_b

    print(f"[INFO] Simulating likes: {len(posts_a)} for {author_a}" + (f", {len(posts_b)} for {author_b}" if posts_b else ""))
    simulate_interactions(user_personal, interaction_plan)
    time.sleep(1)  # Give backend a moment to process
    recs = fetch_timeline(user_personal)
    print_recommendations("Personalized Recommendations (should favor Author_A)", recs)

    # 2. Cold Start Handling
    user_cold = random_user_id("coldstart")
    print(f"[INFO] Using test user_id for cold start: {user_cold}")
    recs_cold = fetch_timeline(user_cold)
    print_recommendations("Cold Start Recommendations (should be generic/popular)", recs_cold)

if __name__ == "__main__":
    main() 