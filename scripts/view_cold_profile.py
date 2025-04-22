#!/usr/bin/env python3
"""
CLI tool for viewing user cold start signal profiles.
Displays details about a user's preferences extracted from their cold start interactions.
"""

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
from tabulate import tabulate

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import required modules
from utils.user_signals import (
    get_user_signals,
    import_user_signals_from_db,
    check_promotion_status,
    should_reenter_cold_start
)

def load_config():
    """Load cold start configuration."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'cold_start_weights.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return json.load(f)
    return {
        "random_ratio": 0.7,
        "weighted_ratio": 0.3,
        "evolution_rate": 0.1,
        "min_weighted_ratio": 0.3,
        "max_weighted_ratio": 1.0
    }

def format_timestamp(timestamp):
    """Format a UNIX timestamp into a readable date/time."""
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    return 'N/A'

def plot_tag_distribution(user_signals):
    """Generate a bar chart of tag distributions."""
    if not user_signals or 'tags' not in user_signals or not user_signals['tags']:
        print("No tag data available for visualization")
        return
    
    # Get top tags
    tags = Counter(user_signals.get('tags', {}))
    top_tags = dict(tags.most_common(10))
    
    # Create bar chart
    plt.figure(figsize=(10, 6))
    plt.bar(top_tags.keys(), top_tags.values(), color='skyblue')
    plt.xlabel('Tags')
    plt.ylabel('Interaction Count')
    plt.title('Top Tags by Interaction Count')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    # Save to temporary file
    temp_file = f"/tmp/corgi_tag_distribution_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    plt.savefig(temp_file)
    plt.close()
    
    print(f"\nTag distribution chart saved to: {temp_file}")
    
    # If running in a GUI environment, try to display the chart
    try:
        plt.show()
    except:
        pass

def plot_interaction_timeline(user_signals):
    """Generate a timeline of user interactions."""
    if not user_signals or 'interaction_history' not in user_signals or not user_signals['interaction_history']:
        print("No interaction history available for visualization")
        return
    
    history = user_signals.get('interaction_history', [])
    
    # Extract timestamps and actions
    timestamps = [entry['timestamp'] for entry in history if 'timestamp' in entry]
    actions = [entry['action_type'] for entry in history if 'action_type' in entry]
    
    if not timestamps:
        return
    
    # Convert to datetime objects
    dates = [datetime.fromtimestamp(ts) for ts in timestamps]
    
    # Create action type mapping for colors
    action_types = list(set(actions))
    colors = plt.cm.tab10(np.linspace(0, 1, len(action_types)))
    action_colors = {action: color for action, color in zip(action_types, colors)}
    
    # Create scatter plot
    plt.figure(figsize=(10, 6))
    
    for action in action_types:
        action_dates = [dates[i] for i in range(len(dates)) if actions[i] == action]
        y_values = [action_types.index(action) for _ in range(len(action_dates))]
        plt.scatter(action_dates, y_values, label=action, color=action_colors[action], s=100)
    
    plt.yticks(range(len(action_types)), action_types)
    plt.xlabel('Date/Time')
    plt.ylabel('Interaction Type')
    plt.title('User Interaction Timeline')
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    plt.tight_layout()
    
    # Save to temporary file
    temp_file = f"/tmp/corgi_interaction_timeline_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    plt.savefig(temp_file)
    plt.close()
    
    print(f"Interaction timeline chart saved to: {temp_file}")
    
    # If running in a GUI environment, try to display the chart
    try:
        plt.show()
    except:
        pass

def display_signal_profile(user_id, user_signals, verbose=False):
    """Display a formatted report of the user's signal profile."""
    if not user_signals:
        print(f"No signal profile found for user: {user_id}")
        return
    
    print("\n" + "="*80)
    print(f"COLD START SIGNAL PROFILE FOR USER: {user_id}")
    print("="*80)
    
    # Basic statistics
    interaction_count = user_signals.get('interaction_count', 0)
    first_interaction = format_timestamp(user_signals.get('first_interaction'))
    last_interaction = format_timestamp(user_signals.get('last_interaction'))
    unique_tags = len(user_signals.get('tags', {}))
    
    print(f"\nINTERACTION SUMMARY:")
    print(f"Total interactions: {interaction_count}")
    print(f"Unique tags: {unique_tags}")
    print(f"First interaction: {first_interaction}")
    print(f"Last interaction: {last_interaction}")
    
    # Promotion status
    promotion_status = check_promotion_status(user_id)
    reentry_status = should_reenter_cold_start(user_id)
    
    print(f"\nSTATUS:")
    print(f"Promotion status: {'PROMOTED' if promotion_status else 'IN COLD START'}")
    print(f"Re-entry eligibility: {'ELIGIBLE' if reentry_status else 'NOT ELIGIBLE'}")
    
    # Display tag preferences
    print("\nTAG PREFERENCES:")
    tags = Counter(user_signals.get('tags', {}))
    if tags:
        tag_table = []
        for tag, count in tags.most_common(10):
            tag_table.append([tag, count, f"{count/interaction_count*100:.1f}%"])
        print(tabulate(tag_table, headers=["Tag", "Count", "Percentage"], tablefmt="simple"))
    else:
        print("No tag data available")
    
    # Display category preferences
    print("\nCATEGORY PREFERENCES:")
    categories = Counter(user_signals.get('categories', {}))
    if categories:
        category_table = []
        for category, count in categories.most_common(5):
            category_table.append([category, count, f"{count/interaction_count*100:.1f}%"])
        print(tabulate(category_table, headers=["Category", "Count", "Percentage"], tablefmt="simple"))
    else:
        print("No category data available")
    
    # Display vibe preferences if available
    if 'vibes' in user_signals and user_signals['vibes']:
        print("\nVIBE PREFERENCES:")
        vibes = Counter(user_signals.get('vibes', {}))
        vibe_table = []
        for vibe, count in vibes.most_common(5):
            vibe_table.append([vibe, count, f"{count/interaction_count*100:.1f}%"])
        print(tabulate(vibe_table, headers=["Vibe", "Count", "Percentage"], tablefmt="simple"))
    
    # Display tone preferences if available
    if 'tones' in user_signals and user_signals['tones']:
        print("\nTONE PREFERENCES:")
        tones = Counter(user_signals.get('tones', {}))
        tone_table = []
        for tone, count in tones.most_common(5):
            tone_table.append([tone, count, f"{count/interaction_count*100:.1f}%"])
        print(tabulate(tone_table, headers=["Tone", "Count", "Percentage"], tablefmt="simple"))
    
    # Display interaction type distribution
    print("\nINTERACTION TYPES:")
    action_types = {}
    for entry in user_signals.get('interaction_history', []):
        action = entry.get('action_type')
        if action:
            action_types[action] = action_types.get(action, 0) + 1
    
    if action_types:
        action_table = []
        for action, count in sorted(action_types.items(), key=lambda x: x[1], reverse=True):
            action_table.append([action, count, f"{count/interaction_count*100:.1f}%"])
        print(tabulate(action_table, headers=["Action Type", "Count", "Percentage"], tablefmt="simple"))
    else:
        print("No interaction type data available")
    
    # If verbose mode is enabled, show full interaction history
    if verbose and 'interaction_history' in user_signals:
        print("\nINTERACTION HISTORY:")
        history_table = []
        for entry in sorted(user_signals['interaction_history'], key=lambda x: x.get('timestamp', 0)):
            history_table.append([
                format_timestamp(entry.get('timestamp')),
                entry.get('post_id', 'N/A'),
                entry.get('action_type', 'N/A'),
                ', '.join(entry.get('tags', [])) or 'N/A',
                entry.get('category', 'N/A')
            ])
        print(tabulate(history_table, 
                       headers=["Timestamp", "Post ID", "Action", "Tags", "Category"], 
                       tablefmt="simple", 
                       maxcolwidths=[20, 15, 10, 30, 15]))
    
    print("\n" + "="*80)

def main():
    """Main CLI function."""
    parser = argparse.ArgumentParser(description='View cold start user signal profiles')
    parser.add_argument('--user', '-u', required=True, help='User ID to view')
    parser.add_argument('--verbose', '-v', action='store_true', help='Show detailed information including full interaction history')
    parser.add_argument('--refresh', '-r', action='store_true', help='Refresh signals from database')
    parser.add_argument('--visualize', '-viz', action='store_true', help='Generate visualizations')
    
    args = parser.parse_args()
    
    # Ensure we have the latest signals from DB
    if args.refresh:
        print(f"Refreshing user signals from database...")
        import_user_signals_from_db()
    
    # Get the user's signal profile
    user_signals = get_user_signals(args.user)
    
    # Display the profile
    display_signal_profile(args.user, user_signals, args.verbose)
    
    # Generate visualizations if requested
    if args.visualize:
        print("\nGenerating visualizations...")
        plot_tag_distribution(user_signals)
        plot_interaction_timeline(user_signals)

if __name__ == "__main__":
    main()