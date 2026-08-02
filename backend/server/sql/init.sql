CREATE TABLE
    IF NOT EXISTS public.draw_history (
        id SERIAL PRIMARY KEY,
        lastX REAL,
        lastY REAL,
        currentX REAL,
        currentY REAL,
        color TEXT,
        size INTEGER
    );

ALTER TABLE public.draw_history ENABLE ROW LEVEL SECURITY;
