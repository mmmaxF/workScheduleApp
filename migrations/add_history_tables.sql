-- Add history_events table
CREATE TABLE IF NOT EXISTS history_events (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES calendar_members(id),
    member_display_name VARCHAR(100) NOT NULL,
    event_date DATE NOT NULL,
    event_type_id INTEGER REFERENCES calendar_event_types(id),
    event_type_name VARCHAR(100),
    event_type_code VARCHAR(50),
    title VARCHAR(200) NOT NULL,
    display_label VARCHAR(100),
    memo TEXT,
    source_type VARCHAR(50) DEFAULT 'manual' NOT NULL,
    source_detail VARCHAR(200),
    original_event_id INTEGER,
    archived_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Add history_aggregations table
CREATE TABLE IF NOT EXISTS history_aggregations (
    id SERIAL PRIMARY KEY,
    member_id INTEGER NOT NULL REFERENCES calendar_members(id),
    member_display_name VARCHAR(100) NOT NULL,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    event_type_id INTEGER REFERENCES calendar_event_types(id),
    event_type_name VARCHAR(100),
    event_type_code VARCHAR(50),
    count INTEGER DEFAULT 0 NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_history_events_member_id ON history_events(member_id);
CREATE INDEX IF NOT EXISTS idx_history_events_event_date ON history_events(event_date);
CREATE INDEX IF NOT EXISTS idx_history_events_event_type_id ON history_events(event_type_id);
CREATE INDEX IF NOT EXISTS idx_history_events_year_month ON history_events(EXTRACT(YEAR FROM event_date), EXTRACT(MONTH FROM event_date));

CREATE INDEX IF NOT EXISTS idx_history_aggregations_member_id ON history_aggregations(member_id);
CREATE INDEX IF NOT EXISTS idx_history_aggregations_year_month ON history_aggregations(year, month);
CREATE INDEX IF NOT EXISTS idx_history_aggregations_event_type_id ON history_aggregations(event_type_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_history_aggregations_unique ON history_aggregations(member_id, year, month, event_type_id);
