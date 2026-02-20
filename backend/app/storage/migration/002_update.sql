ALTER TABLE instruments 
ADD COLUMN watch_list INTEGER;

-- Adding stock scoring and taxonomy
ALTER TABLE instruments ADD COLUMN overall_score INTEGER;
ALTER TABLE instruments ADD COLUMN risk_score INTEGER;
ALTER TABLE instruments ADD COLUMN sector TEXT;


