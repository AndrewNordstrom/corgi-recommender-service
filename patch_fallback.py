import re

# Read the file
with open('routes/recommendations.py', 'r') as f:
    content = f.read()

# Replace the fallback section
old_pattern = r'''                    recommendations\.append\(\{
                        "id": f"rec_cold_\{i\}",
                        "content": post,
                        "score": 0\.7,
                        "reason": "Trending content",
                        "insertion_point": \(i \+ 1\) \* 6
                    \}\)'''

new_code = '''                    # Enhanced metadata for fallback recommendations too
                    score = 0.7
                    strength = "Moderately"
                    strength_emoji = "📈"
                    reason = "Trending content"
                    
                    recommendations.append({
                        "id": f"rec_cold_{i}",
                        "content": post,
                        "score": score,
                        "reason": reason,
                        "strength": strength,
                        "strength_emoji": strength_emoji,
                        "confidence": f"{int(score * 100)}%",
                        "insertion_point": (i + 1) * 6
                    })'''

updated_content = re.sub(old_pattern, new_code, content)

# Write back the file
with open('routes/recommendations.py', 'w') as f:
    f.write(updated_content)

print("✅ Fallback recommendations enhanced with metadata") 