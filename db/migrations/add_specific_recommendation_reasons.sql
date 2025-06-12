-- Add specific recommendation reason fields to support enhanced recommendation tags
-- This migration adds fields to store the detailed reason a post was recommended

-- Add fields to crawled_posts table to store discovery-specific reasons
ALTER TABLE crawled_posts 
ADD COLUMN IF NOT EXISTS recommendation_reason_type VARCHAR(50) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS recommendation_reason_detail TEXT DEFAULT NULL;

-- Add fields to post_rankings table to store specific recommendation reasons
ALTER TABLE post_rankings 
ADD COLUMN IF NOT EXISTS reason_type VARCHAR(50) DEFAULT NULL,
ADD COLUMN IF NOT EXISTS reason_detail TEXT DEFAULT NULL;

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_crawled_posts_reason_type ON crawled_posts(recommendation_reason_type);
CREATE INDEX IF NOT EXISTS idx_post_rankings_reason_type ON post_rankings(reason_type);

-- Update SQLite compatibility for the new fields
-- These will be handled by the application layer for existing records

-- Populate reason_type for existing records based on discovery metadata
UPDATE crawled_posts 
SET recommendation_reason_type = 'hashtag_trending'
WHERE discovery_metadata LIKE '%hashtag_stream%' 
AND recommendation_reason_type IS NULL;

UPDATE crawled_posts 
SET recommendation_reason_type = 'author_network'
WHERE discovery_metadata LIKE '%follow_relationships%' 
AND recommendation_reason_type IS NULL;

UPDATE crawled_posts 
SET recommendation_reason_type = 'general_trending'
WHERE discovery_metadata LIKE '%timeline%' 
AND recommendation_reason_type IS NULL; 