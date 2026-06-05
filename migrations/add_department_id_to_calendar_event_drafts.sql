-- Add department_id column to calendar_event_drafts table
ALTER TABLE calendar_event_drafts ADD COLUMN IF NOT EXISTS department_id INTEGER REFERENCES departments(id);
