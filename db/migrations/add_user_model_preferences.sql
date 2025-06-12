-- Migration: Add user_model_preferences table
-- This table stores which model variant each user has activated for personalized recommendations

CREATE TABLE IF NOT EXISTS user_model_preferences (
    id SERIAL PRIMARY KEY,
    user_alias VARCHAR(255) UNIQUE NOT NULL,
    active_variant_id INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign key constraint to ab_variants table
    CONSTRAINT fk_user_model_preferences_variant 
        FOREIGN KEY (active_variant_id) 
        REFERENCES ab_variants(id) 
        ON DELETE CASCADE
);

-- Index for fast lookups by user
CREATE INDEX IF NOT EXISTS idx_user_model_preferences_user_alias 
    ON user_model_preferences(user_alias);

-- Index for analytics queries by variant
CREATE INDEX IF NOT EXISTS idx_user_model_preferences_variant_id 
    ON user_model_preferences(active_variant_id);

-- Add comment for documentation
COMMENT ON TABLE user_model_preferences IS 'Stores the active model variant preference for each user';
COMMENT ON COLUMN user_model_preferences.user_alias IS 'Pseudonymized user identifier';
COMMENT ON COLUMN user_model_preferences.active_variant_id IS 'ID of the currently active model variant for this user';
COMMENT ON COLUMN user_model_preferences.updated_at IS 'Timestamp when the preference was last updated';
COMMENT ON COLUMN user_model_preferences.created_at IS 'Timestamp when the preference was first created'; 