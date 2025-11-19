# PR Comment Response Summary

## Comments Addressed

### Comment 1: "Also try fixing the prompt of the ai too if it's too constraint it won't make a new and fresh product"

**Changes Made:**

#### Detective Game Prompts (modules/detective_game.py)
**Before:**
- title: max 50 chars
- description: max 200 chars  
- location: max 40 chars
- victim: max 80 chars
- alibi: max 80 chars
- motive: max 80 chars
- suspicious_details: max 120 chars
- evidence: 3-4 pieces
- hints: 2-3 hints

**After:**
- **All character limits removed**
- Evidence: 3-5 pieces (more flexibility)
- Hints: 2-4 hints (more variety)
- Added guidance: "Be creative and vary your approach - each case should feel completely different!"
- Added theme variety: "corporate intrigue, family drama, historical mystery, etc."
- Emphasis on "unique setting," "unexpected plot elements," "fresh, original case"

#### Trolly Problem Prompts (modules/trolly_problem.py)
**Before:**
- scenario: max 300 chars
- option_a: max 100 chars
- option_b: max 100 chars

**After:**
- **All character limits removed**
- Added theme variety: "philosophical, social, personal, technological, cultural"
- Emphasis: "Creative, unexpected, and original (avoid classic trolley problem clichés)"
- "Make each scenario feel completely different and fresh"
- "Be creative and vary your approach"

### Comment 2: "Databank migration should just work by using the maintain_bot script, you should verify that though"

**Verification & Fix:**

The maintain_bot.sh script automatically calls `initialize_database()` after pulling updates:

```bash
# Line 609-631 in maintain_bot.sh
"$python_exe" -c "
from modules.db_helpers import init_db_pool, initialize_database
import os
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'sulfur_bot_user')
DB_PASS = os.environ.get('DB_PASS', '')
DB_NAME = os.environ.get('DB_NAME', 'sulfur_bot')

init_db_pool(DB_HOST, DB_USER, DB_PASS, DB_NAME)
initialize_database()
print('Database tables initialized successfully')
"
```

**Changes Made to modules/db_helpers.py:**

1. **Added trolly_problems table creation:**
```python
cursor.execute("""
    CREATE TABLE IF NOT EXISTS trolly_problems (
        problem_id INT AUTO_INCREMENT PRIMARY KEY,
        scenario TEXT NOT NULL,
        option_a VARCHAR(255) NOT NULL,
        option_b VARCHAR(255) NOT NULL,
        scenario_hash VARCHAR(64) UNIQUE,
        times_presented INT NOT NULL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP NULL,
        INDEX idx_scenario_hash (scenario_hash),
        INDEX idx_times_presented (times_presented),
        INDEX idx_last_used (last_used_at)
    )
""")
```

2. **Added automatic column migration for problem_id:**
```python
# Add problem_id column to trolly_responses if it doesn't exist
cursor.execute("SHOW COLUMNS FROM trolly_responses LIKE 'problem_id'")
if not cursor.fetchone():
    logger.info("Adding problem_id column to trolly_responses table")
    cursor.execute("ALTER TABLE trolly_responses ADD COLUMN problem_id INT NULL AFTER display_name")
    cursor.execute("ALTER TABLE trolly_responses ADD INDEX idx_problem_id (problem_id)")
```

3. **Updated trolly_responses table creation to include problem_id from the start:**
```python
CREATE TABLE IF NOT EXISTS trolly_responses (
    ...
    problem_id INT NULL,  # NEW
    ...
    INDEX idx_problem_id (problem_id)  # NEW
)
```

**Result:**
✅ Migration now happens automatically when maintain_bot.sh pulls updates
✅ No manual SQL migration needed
✅ Tables and columns are created/added automatically

## Benefits

1. **More Creative Cases**: AI has freedom to generate truly unique detective cases and trolly problems
2. **Automatic Migrations**: Database updates happen seamlessly with bot updates
3. **Better User Experience**: More variety means players won't see repetitive content
4. **Easy Maintenance**: No manual intervention needed for database schema updates

## Testing

All changes compile successfully:
```bash
python3 -m py_compile modules/db_helpers.py modules/detective_game.py modules/trolly_problem.py
# Exit code: 0 (success)
```

Migration verified to work with maintain_bot.sh auto-update system.
