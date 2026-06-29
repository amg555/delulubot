# Delulubot Improvement TODO

## Current Status: IN PROGRESS

## Add OpenCode + GLM5 Fallbacks - TODO

### Step 1: Update requirements.txt
- [x] 1. Add openai package for OpenAI-compatible API calls

### Step 2: Update .env.example
- [x] 2. Add OPENCODE_API_KEY
- [x] 3. Add GLM_API_KEY (NVIDIA)
- [x] 4. Add OPENCODE_MODEL (default: opencode)
- [x] 5. Add GLM_MODEL (default: glm-4)

### Step 3: Update delulu_bot.py
- [x] 6. Add OpenAI import and configuration
- [x] 7. Add OpenCode response function
- [x] 8. Add GLM response function
- [x] 9. Integrate fallbacks into get_delulu_response()
- [x] 10. Update /status command to show new models

### Step 4: Testing
- [ ] 11. Test OpenCode fallback
- [ ] 12. Test GLM fallback
- [ ] 13. Verify fallback chain works

