-- Migration: Add audio storage path to raw_instagram_reels
-- Run this if you already executed 01_create_reels_table.sql

ALTER TABLE raw_instagram_reels
ADD COLUMN IF NOT EXISTS storage_audio_path TEXT;

COMMENT ON COLUMN raw_instagram_reels.storage_audio_path IS 'Path to extracted audio in Supabase Storage (e.g., "audio/DRLS0KOAdv2.mp3")';
