-- Add rich content fields to crawled_posts table
-- These fields will store JSON data for media attachments, cards, and polls

ALTER TABLE crawled_posts 
ADD COLUMN IF NOT EXISTS media_attachments JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS card JSONB DEFAULT NULL,
ADD COLUMN IF NOT EXISTS poll JSONB DEFAULT NULL,
ADD COLUMN IF NOT EXISTS mentions JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS emojis JSONB DEFAULT '[]'::jsonb,
ADD COLUMN IF NOT EXISTS url TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS in_reply_to_id TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS in_reply_to_account_id TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS visibility TEXT DEFAULT 'public',
ADD COLUMN IF NOT EXISTS reblog JSONB DEFAULT NULL,
ADD COLUMN IF NOT EXISTS author_acct TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS author_display_name TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS author_avatar TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS author_note TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS author_followers_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS author_following_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS author_statuses_count INTEGER DEFAULT 0;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_crawled_posts_visibility ON crawled_posts(visibility);
CREATE INDEX IF NOT EXISTS idx_crawled_posts_has_media ON crawled_posts((jsonb_array_length(media_attachments) > 0));
CREATE INDEX IF NOT EXISTS idx_crawled_posts_has_card ON crawled_posts((card IS NOT NULL));
CREATE INDEX IF NOT EXISTS idx_crawled_posts_has_poll ON crawled_posts((poll IS NOT NULL));

-- Update existing posts to have proper visibility
UPDATE crawled_posts SET visibility = 'public' WHERE visibility IS NULL; 