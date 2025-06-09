import re

with open('routes/recommendations.py', 'r') as f:
    content = f.read()

# Find and replace the recommendation building section
old_section = '''                recommendations.append({
                    "id": f"rec_{rec.get('id', i)}",
                    "content": seamless_status,
                    "score": rec.get('score', 0.5),
                    "reason": rec.get('reason', 'Recommended for you'),
                    "insertion_point": (i + 1) * 6  # Insert every 6 posts
                })'''

new_section = '''                # Enhanced reasoning based on context and score
                score = rec.get('score', 0.5)
                reason_details = rec.get('reason_details', {})
                
                # Generate descriptive reason and strength indicators
                if score >= 0.8:
                    strength = "Highly"
                    strength_emoji = "🔥"
                elif score >= 0.6:
                    strength = "Moderately" 
                    strength_emoji = "📈"
                else:
                    strength = "Mildly"
                    strength_emoji = "💡"
                
                # Build reason based on available context
                base_reason = rec.get('reason', 'Recommended for you')
                if 'similar_authors' in reason_details:
                    reason = f"Similar to posts by people you follow"
                elif 'trending' in reason_details:
                    reason = f"Trending in your network"
                elif 'topic_match' in reason_details:
                    reason = f"Related to recent posts you engaged with"
                elif timeline_type == 'local':
                    reason = f"Popular in your local community"
                elif timeline_type == 'public':
                    reason = f"Trending globally"
                else:
                    reason = base_reason
                
                recommendations.append({
                    "id": f"rec_{rec.get('id', i)}",
                    "content": seamless_status,
                    "score": score,
                    "reason": reason,
                    "strength": strength,
                    "strength_emoji": strength_emoji,
                    "confidence": f"{int(score * 100)}%",
                    "insertion_point": (i + 1) * 6  # Insert every 6 posts
                })'''

content = content.replace(old_section, new_section)

with open('routes/recommendations.py', 'w') as f:
    f.write(content)

print('✅ API enhanced with better recommendation metadata') 