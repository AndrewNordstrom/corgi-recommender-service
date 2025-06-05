# Corgi Recommender Service — Demo Walkthrough

This guide provides a step-by-step walkthrough for demonstrating the Corgi Recommender Service MVP.

**Duration:** 5-7 minutes

## Prerequisites
- Corgi Recommender Service running on localhost:5001
- PostgreSQL database running and initialized
- Demo users and posts created (`scripts/create_demo_users.py`)
- Elk or another Mastodon client configured to use localhost:5001 as proxy

## 1. Introduction (30 seconds)

"Today I'm going to demonstrate our Corgi Recommender Service, which acts as a transparent middleware layer between Mastodon clients and servers. It enhances the user experience by providing personalized recommendations while respecting user privacy preferences."

## 2. Architecture Overview (1 minute)

"The system has three main components:
1. **Core API** - Handles interactions, posts, and recommendation generation
2. **Proxy Layer** - Transparently routes traffic between clients and Mastodon servers
3. **Agent Framework** - For testing and validation with synthetic users

Let me show you how it works in practice."

## 3. API Documentation (1 minute)

"First, let's look at the API documentation to understand the available endpoints."

1. Open browser to http://localhost:5001/api/v1/docs
2. Showcase the interactive OpenAPI documentation
3. Highlight key endpoints:
   - `/api/v1/recommendations` - For getting personalized content
   - `/api/v1/interactions` - For logging user engagement
   - `/api/v1/privacy` - For controlling data collection

## 4. Demo Users (1 minute)

"We've created two demo user profiles to illustrate how the system adapts to different preferences:"

1. Open a new terminal window
2. Run:
   ```bash
   curl http://localhost:5001/api/v1/privacy/settings?user_id=alice_tech
   ```
3. Show Alice's "full" privacy settings that enable personalization
4. Run:
   ```bash
   curl http://localhost:5001/api/v1/privacy/settings?user_id=bob_privacy
   ```
5. Show Bob's "none" privacy setting that disables tracking
6. Explain how this affects recommendations

## 5. Viewing Recommendations (1 minute)

"Let's see what recommendations our system generates for each user profile."

1. For Alice (tech enthusiast):
   ```bash
   curl http://localhost:5001/api/v1/recommendations?user_id=alice_tech | jq
   ```
2. Point out tech-focused content in the results
3. For Bob (privacy-focused):
   ```bash
   curl http://localhost:5001/api/v1/recommendations?user_id=bob_privacy | jq
   ```
4. Note the generic, non-personalized recommendations due to privacy settings

## 6. Live Proxy Demonstration (2 minutes)

"Now let's see the system in action through a real Mastodon client."

1. Open the Elk client configured to use our proxy
2. Log in as a test user
3. Point out the blended timeline with recommended posts
   - "Notice how some posts have a 'Recommended' badge - these are injected by our service"
4. Interact with a post by favoriting it
5. Show the logged interaction:
   ```bash
   curl http://localhost:5001/api/v1/interactions | jq
   ```

## 7. Privacy Settings Change (1 minute)

"Users can change their privacy settings at any time, and the system will adapt accordingly."

1. Demonstrate changing privacy settings:
   ```bash
   curl -X POST http://localhost:5001/api/v1/privacy/settings \
     -H "Content-Type: application/json" \
     -d '{"user_id": "alice_tech", "tracking_level": "limited"}'
   ```
2. Show how recommendations change:
   ```bash
   curl http://localhost:5001/api/v1/recommendations?user_id=alice_tech | jq
   ```
3. Explain that limited tracking provides moderate personalization

## 8. Validator Demonstration (30 seconds)

"We've built comprehensive validation tools to ensure the system works correctly."

1. Run the validator:
   ```bash
   python corgi_validator.py --api-base=http://localhost:5001 --api-prefix=/api/v1 --verbose
   ```
2. Show the validator report with passing tests

## 9. Conclusion (30 seconds)

"In this demo, we've seen how the Corgi Recommender Service:
1. Transparently enhances Mastodon with personalized content
2. Respects user privacy preferences
3. Logs interactions to improve future recommendations
4. Provides a robust API for integration

For the next phase, we'll be implementing OAuth support and refining the recommendation algorithm based on user feedback."

## Q&A

Be prepared to address questions about:
- Scaling for production usage
- Performance optimizations
- Security considerations
- Plans for A/B testing
- Integration with other Mastodon clients