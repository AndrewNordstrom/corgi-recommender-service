# Future Tasks / Notes

## API Improvements
- Add OpenAPI UI endpoint at /api/v1/docs (with Swagger UI or ReDoc)
- Consider adding /v1 route aliases for Mastodon compatibility
- Add basic auth or OAuth2 before proxy rollout
- Support pagination for recommendations and timeline endpoints

## Database & Data Management
- Track synthetic data seeds separately in the DB for cleanup
- Implement scheduled cleanup of old rankings and unused data
- Add database migration system for future schema changes
- Consider sharding strategy for high-volume deployments

## Documentation
- Consider exporting docs to GitHub Pages or Vercel
- Add API flow diagrams to documentation
- Generate Python API client from OpenAPI spec
- Create integration examples for common Mastodon clients

## Performance & Scaling
- Add Redis caching layer for recommendation results
- Create worker queue for asynchronous ranking generation
- Implement proper rate limiting for API endpoints
- Add metrics and dashboards for monitoring recommendation quality

## Testing & Validation
- Add integration tests for full API flow
- Create performance benchmarks for recommendation algorithm
- Implement A/B testing framework for algorithm variations
- Add automated test for OpenAPI spec compliance