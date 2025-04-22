# Future Tasks / Notes

## API Improvements
- ✅ Add OpenAPI UI endpoint at /api/v1/docs (with Swagger UI)
- ✅ Set up OAuth scaffold routes for Phase 3
- ✅ Add Mastodon-compatible API endpoints for proxy support
- ✅ Implement transparent proxy middleware
- Support pagination for recommendations and timeline endpoints
- Add rate limiting for public API endpoints

## Database & Data Management
- Track synthetic data seeds separately in the DB for cleanup
- Implement scheduled cleanup of old rankings and unused data
- Add database migration system for future schema changes
- Consider sharding strategy for high-volume deployments

## Documentation
- ✅ Create comprehensive proxy middleware documentation
- ✅ Add detailed configuration guides for server options
- ✅ Document client library integration patterns
- Consider exporting docs to GitHub Pages or Vercel
- Add API flow diagrams to documentation
- Generate Python API client from OpenAPI spec

## Performance & Scaling
- ✅ Add metrics collection for proxy performance
- Add Redis caching layer for recommendation results
- Create worker queue for asynchronous ranking generation
- Implement proper rate limiting for API endpoints
- Add metrics and dashboards for monitoring recommendation quality

## Testing & Validation
- ✅ Fix validator compatibility with API paths
- ✅ Add demo user fixtures for testing
- ✅ Implement SSL/HTTPS configuration options
- ✅ Add CORS support for local development
- Add integration tests for full API flow
- Create performance benchmarks for recommendation algorithm
- Implement A/B testing framework for algorithm variations
- Add automated test for OpenAPI spec compliance

## Agent Framework
- ✅ Create robust agent framework for synthetic users
- ✅ Add multiple user profiles with different preferences
- ✅ Implement privacy settings testing
- Implement actual UI interaction via Claude's computer_use tool
- Develop test runner to execute multiple agents concurrently
- Add feedback collection from agent experiences
- Extract the agent framework to its own repository
- Add support for different UI contexts (desktop vs mobile)
- Implement UI snapshot capture for better debugging
- Create dashboard to visualize agent test results

## Proxy Middleware
- ✅ Implement transparent proxy with timeline injection
- ✅ Add privacy-aware recommendation blending
- ✅ Create debug routes for proxy testing
- ✅ Add metrics collection for proxy performance
- ✅ Implement cold start timeline for new users
- Implement caching for frequently accessed endpoints
- Add request throttling for high-volume deployments
- Create more granular logging controls

## Cold Start Strategy
- ✅ Implement cold start mode for users who follow no one
- ✅ Create curated content sets for new users
- ✅ Add logging of cold start interactions
- ✅ Support manual cold start testing via query flag
- ✅ Document cold start strategy comprehensively
- ✅ Implement adaptive cold start based on early user signals
- ✅ Implement gradual transition mechanism from cold start to personalized content
- ✅ Add user signal tracking for personalization
- ✅ Create CLI tools for analyzing user signal profiles
- ✅ Implement cold start fallback for anonymous users
- Tune ranking logic for better cold start selection (prioritize diverse content)
- Create multiple cold start content sets for different regions/languages
- Add A/B testing framework for cold start content variations
- Develop analytics dashboard for measuring cold start effectiveness
- Add user feedback collection for cold start posts
- Create scheduled job to refresh cold start content regularly
- Develop ML model to optimize cold start post selection