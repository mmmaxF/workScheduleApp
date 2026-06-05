-- Add department_id column to calendar_events table
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS department_id INTEGER REFERENCES departments(id);
