# Personality Evolution System - Implementation Guide

## Quick Verification

After pulling these changes, verify the implementation works:

### 1. Check File Structure

```bash
# Verify all new files exist
ls -la modules/personality_evolution.py
ls -la scripts/db_migrations/016_personality_evolution.sql
ls -la docs/PERSONALITY_EVOLUTION.md

# Check git diff
git diff origin/main..HEAD --stat
```

### 2. Syntax Check

```bash
# Check Python syntax
python3 -m py_compile modules/personality_evolution.py
python3 -m py_compile modules/bot_mind.py

# Parse bot.py
python3 -m ast bot.py >/dev/null && echo "✓ No syntax errors"
```

### 3. Database Migration

```bash
# Run the migration
mysql -u sulfur_bot_user -p sulfur_bot < scripts/db_migrations/016_personality_evolution.sql

# Verify tables were created
mysql -u sulfur_bot_user -p sulfur_bot -e "SHOW TABLES LIKE '%personality%'; SHOW TABLES LIKE '%learning%'; SHOW TABLES LIKE '%memory%';"
```

Expected tables:
- personality_evolution
- interaction_learnings
- semantic_memory
- reflection_sessions
- conversation_feedback

### 4. Test Bot Startup

```bash
# Start bot (it should load without errors)
python3 bot.py

# Watch for these log messages:
# - "Loaded evolved personality from database"
# - "Personality maintenance task started"
# - "Daily reflection task started"
```

### 5. Test Integration

Once bot is running, test these features:

**Interaction Learning**:
1. Send a message to the bot
2. Check logs for: "Recorded learning from interaction"
3. Query database: `SELECT * FROM interaction_learnings ORDER BY created_at DESC LIMIT 5;`

**Reaction Tracking**:
1. React to a bot message with 👍
2. Check logs for: "Could not record reaction feedback" (ok if DB not set up) or success
3. Query database: `SELECT * FROM conversation_feedback ORDER BY created_at DESC LIMIT 5;`

**Personality Context**:
1. Send a message to the bot
2. Bot's response should be informed by evolved personality
3. Check logs for: "Added evolved personality context to prompt"

### 6. Verify Periodic Tasks

Wait 6-24 hours and check logs for:
- `[INFO] Personality maintenance completed` (every 6 hours)
- `[INFO] Reflection completed: ...` (every 24 hours)

Or manually trigger by restarting bot (tasks run on startup).

## Manual Functional Test

```python
# Create a simple test script
cat > test_import.py << 'EOF'
import sys
sys.path.insert(0, '.')

# Test import
from modules import personality_evolution
print("✓ Import successful")

# Test function existence
functions = [
    'get_current_personality',
    'evolve_personality_trait',
    'record_learning',
    'get_personality_context_for_prompt',
]

for func in functions:
    if hasattr(personality_evolution, func):
        print(f"✓ {func} exists")
    else:
        print(f"✗ {func} missing")
EOF

python3 test_import.py
```

## Expected Behavior

### Before Implementation
- Bot responses are generic
- No learning from interactions
- Personality is static
- No memory of patterns

### After Implementation
- Bot responses include evolved personality context
- Learns patterns from conversations
- Personality gradually evolves based on feedback
- Remembers important information in semantic memory
- Self-reflects daily on its behavior

## Monitoring

### Key Log Messages

```bash
# Personality evolution
grep "Personality evolved" logs/*.log

# Learning events
grep "learning recorded" logs/*.log -i

# Reflections
grep "Reflection completed" logs/*.log

# Context enhancement
grep "Added evolved personality context" logs/*.log
```

### Database Queries

```sql
-- Check personality evolution over time
SELECT 
    trait_name, 
    trait_value, 
    reason, 
    created_at 
FROM personality_evolution 
ORDER BY trait_name, created_at DESC 
LIMIT 50;

-- View active learnings
SELECT 
    learning_type, 
    learning_content, 
    confidence, 
    interaction_count,
    relevance_score
FROM interaction_learnings 
WHERE relevance_score > 0.3
ORDER BY confidence DESC, interaction_count DESC
LIMIT 20;

-- Check semantic memories
SELECT 
    memory_type, 
    memory_content, 
    importance, 
    access_count
FROM semantic_memory 
ORDER BY importance DESC, access_count DESC
LIMIT 10;

-- Recent reflections
SELECT 
    reflection_content, 
    insights_generated,
    created_at
FROM reflection_sessions 
ORDER BY created_at DESC 
LIMIT 5;

-- Feedback patterns
SELECT 
    feedback_type,
    AVG(feedback_value) as avg_value,
    COUNT(*) as count
FROM conversation_feedback
WHERE created_at > DATE_SUB(NOW(), INTERVAL 7 DAY)
GROUP BY feedback_type;
```

## Troubleshooting

### Bot won't start
- Check syntax: `python3 -m py_compile modules/personality_evolution.py`
- Check imports: `python3 -c "from modules import personality_evolution"`
- Check bot.py: `python3 -m ast bot.py`

### No learning happening
- Verify tasks are running: Check logs for "personality_maintenance_task"
- Check database connection: Ensure MySQL is accessible
- Verify migration ran: `SHOW TABLES LIKE '%learning%';`

### Personality not evolving
- Need more interactions (evolution is gradual)
- Check database: `SELECT COUNT(*) FROM personality_evolution;`
- Increase evolution rates in `modules/personality_evolution.py`

### Reflection not working
- Ensure Gemini API key is valid
- Check reflection task started: Look for "Daily reflection task started" in logs
- Wait 24 hours or restart bot to trigger first reflection

## Performance Notes

- **Database Queries**: Optimized with proper indexes
- **Memory Usage**: Learnings are limited to top 10 per context
- **Evolution Rate**: Slow and gradual (0.01-0.05 per interaction)
- **Maintenance**: Auto-cleanup every 6 hours
- **Reflection**: Once per 24 hours (low overhead)

## Success Criteria

✅ Bot starts without errors
✅ Personality loads from database
✅ Learnings are recorded after interactions
✅ Personality context is added to prompts
✅ Periodic tasks run successfully
✅ Database tables populated over time
✅ Bot responses become progressively more contextual

## Next Steps After Verification

1. **Monitor for 1 week**: Let personality evolve naturally
2. **Check evolution**: Query personality_evolution table
3. **Review learnings**: See what patterns emerged
4. **Read reflections**: Check what bot learned about itself
5. **Adjust if needed**: Tune evolution rates or thresholds

See `docs/PERSONALITY_EVOLUTION.md` for complete documentation.
