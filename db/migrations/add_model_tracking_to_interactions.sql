-- Migration: Add model tracking to interactions and create performance summary table
-- This enables tracking which model was responsible for each recommendation interaction

-- Add model_variant_id to interactions table
ALTER TABLE interactions 
ADD COLUMN IF NOT EXISTS model_variant_id INTEGER;

-- Add recommendation_id to track the specific recommendation that led to the interaction
ALTER TABLE interactions 
ADD COLUMN IF NOT EXISTS recommendation_id TEXT;

-- Add index for performance queries
CREATE INDEX IF NOT EXISTS idx_interactions_model_variant 
ON interactions(model_variant_id);

CREATE INDEX IF NOT EXISTS idx_interactions_model_created 
ON interactions(model_variant_id, created_at);

-- Create model_performance_summary table for aggregated metrics
CREATE TABLE IF NOT EXISTS model_performance_summary (
    id SERIAL PRIMARY KEY,
    variant_id INTEGER NOT NULL,
    date_hour TIMESTAMP NOT NULL,
    impressions INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    bookmarks INTEGER DEFAULT 0,
    reblogs INTEGER DEFAULT 0,
    engagement_rate DECIMAL(5,4) DEFAULT 0.0,
    avg_response_time DECIMAL(8,2) DEFAULT 0.0,
    total_users INTEGER DEFAULT 0,
    unique_posts INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint to prevent duplicate aggregations
    CONSTRAINT unique_variant_hour UNIQUE (variant_id, date_hour),
    
    -- Foreign key to ab_variants table
    CONSTRAINT fk_model_performance_variant 
        FOREIGN KEY (variant_id) 
        REFERENCES ab_variants(id) 
        ON DELETE CASCADE
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_model_performance_variant_date 
ON model_performance_summary(variant_id, date_hour);

CREATE INDEX IF NOT EXISTS idx_model_performance_date 
ON model_performance_summary(date_hour);

CREATE INDEX IF NOT EXISTS idx_model_performance_engagement 
ON model_performance_summary(variant_id, engagement_rate);

-- Add comments for documentation
COMMENT ON TABLE model_performance_summary IS 'Hourly aggregated performance metrics for each model variant';
COMMENT ON COLUMN model_performance_summary.variant_id IS 'ID of the model variant being measured';
COMMENT ON COLUMN model_performance_summary.date_hour IS 'Hour-truncated timestamp for aggregation period';
COMMENT ON COLUMN model_performance_summary.impressions IS 'Number of recommendations shown to users';
COMMENT ON COLUMN model_performance_summary.likes IS 'Number of like interactions';
COMMENT ON COLUMN model_performance_summary.clicks IS 'Number of click interactions';
COMMENT ON COLUMN model_performance_summary.engagement_rate IS 'Overall engagement rate (interactions/impressions)';
COMMENT ON COLUMN model_performance_summary.avg_response_time IS 'Average response time for recommendations in milliseconds';

-- Create function to update engagement rate automatically
CREATE OR REPLACE FUNCTION update_engagement_rate()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate engagement rate as (total interactions / impressions)
    IF NEW.impressions > 0 THEN
        NEW.engagement_rate = (NEW.likes + NEW.clicks + NEW.bookmarks + NEW.reblogs)::DECIMAL / NEW.impressions;
    ELSE
        NEW.engagement_rate = 0.0;
    END IF;
    
    NEW.updated_at = CURRENT_TIMESTAMP;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update engagement rate
CREATE TRIGGER trigger_update_engagement_rate
    BEFORE INSERT OR UPDATE ON model_performance_summary
    FOR EACH ROW
    EXECUTE FUNCTION update_engagement_rate(); 