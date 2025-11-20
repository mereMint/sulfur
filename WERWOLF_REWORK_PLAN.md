# Werwolf Game Rework Implementation Plan

## Overview
The Werwolf game needs to be reworked so that only roles owned by the game creator are available in the game, with a UI for selecting/deselecting which purchased roles to include.

## Current State
- Roles are assigned automatically based on player count
- All special roles (Seherin, Hexe, Dönerstopfer, Jäger, Amor, Der Weiße) can appear
- Role assignment logic is in `modules/werwolf.py`, lines 280-308
- Role purchases are tracked via `has_feature_unlock(user_id, 'werwolf_role_<rolename>')`

## Required Changes

### 1. Role Ownership Check
**Location**: `modules/werwolf.py` - `start_game()` method

**Implementation**:
```python
async def get_available_roles(self, starter_id, db_helpers):
    """Get roles available based on what the starter owns."""
    available_special_roles = []
    
    # Check each special role
    roles_to_check = ['seherin', 'hexe', 'dönerstopfer', 'jäger', 'amor', 'der_weisse']
    role_mapping = {
        'seherin': SEHERIN,
        'hexe': HEXE,
        'dönerstopfer': DÖNERSTOPFER,
        'jäger': JÄGER,
        'amor': AMOR,
        'der_weisse': DER_WEISSE
    }
    
    for role_key in roles_to_check:
        has_role = await db_helpers.has_feature_unlock(starter_id, f'werwolf_role_{role_key}')
        if has_role:
            available_special_roles.append(role_mapping[role_key])
    
    return available_special_roles
```

### 2. Role Selection UI
**Location**: Add new view class before WerwolfGame creation

**Implementation**:
```python
class WerwolfRoleSelectionView(discord.ui.View):
    """Allow game creator to select which roles to include."""
    
    def __init__(self, starter_id, available_roles, channel):
        super().__init__(timeout=120)
        self.starter_id = starter_id
        self.selected_roles = set(available_roles)  # All selected by default
        self.channel = channel
        
        # Create toggle buttons for each role
        for role in available_roles:
            self.add_item(RoleToggleButton(role))
    
    @discord.ui.button(label="Spiel starten", style=discord.ButtonStyle.success)
    async def start_game_button(self, interaction, button):
        """Start game with selected roles."""
        # Proceed with game creation using self.selected_roles
        pass

class RoleToggleButton(discord.ui.Button):
    """Toggle button for individual roles."""
    
    def __init__(self, role_name):
        self.role_name = role_name
        self.is_selected = True
        super().__init__(
            label=role_name,
            style=discord.ButtonStyle.primary,
            custom_id=f"role_{role_name}"
        )
    
    async def callback(self, interaction):
        self.is_selected = not self.is_selected
        self.style = discord.ButtonStyle.primary if self.is_selected else discord.ButtonStyle.secondary
        # Update parent view's selected_roles
```

### 3. Modified Role Assignment
**Location**: `modules/werwolf.py` - `start_game()` method

**Changes**:
- Replace current automatic role assignment logic (lines 280-302)
- Use only the roles that were selected in the UI
- Still account for player count to determine how many of each role

```python
async def start_game(self, config, gemini_key, openai_key, db_helpers, selected_roles=None):
    # ... existing code ...
    
    # Build role pool from selected roles
    role_pool = []
    
    # Calculate how many of each special role based on player count
    role_counts = self._calculate_role_counts(player_count)
    
    # Only include roles that were selected
    for role in selected_roles:
        if role == SEHERIN and role_counts['seherin'] > 0:
            role_pool.append(SEHERIN)
        elif role == HEXE and role_counts['hexe'] > 0:
            role_pool.append(HEXE)
        # ... etc for each role
    
    # Add werewolves (always included)
    num_werwolfe = max(1, player_count // 3)
    role_pool.extend([WERWOLF] * num_werwolfe)
    
    # Fill remaining with villagers
    num_dorfbewohner = player_count - len(role_pool)
    role_pool.extend([DORFBEWOHNER] * num_dorfbewohner)
    
    # Shuffle and assign
    random.shuffle(role_pool)
    # ... rest of assignment logic
```

### 4. Command Integration
**Location**: `bot.py` - `/werwolf` command

**Changes**:
- When game is created, show role selection UI before starting
- Pass selected roles to `start_game()`

```python
@tree.command(name="werwolf")
async def werwolf(interaction: discord.Interaction):
    # ... existing setup ...
    
    # Get available roles for this user
    available_roles = await get_available_werwolf_roles(interaction.user.id)
    
    if not available_roles:
        # User has no special roles unlocked
        # Show purchase prompt
        pass
    
    # Show role selection UI
    selection_view = WerwolfRoleSelectionView(
        interaction.user.id,
        available_roles,
        interaction.channel
    )
    
    embed = discord.Embed(
        title="🐺 Werwolf Rollen-Auswahl",
        description="Wähle, welche Rollen in diesem Spiel verfügbar sein sollen:",
        color=discord.Color.blue()
    )
    
    await interaction.followup.send(embed=embed, view=selection_view, ephemeral=True)
```

### 5. Visual Updates
**Location**: `modules/werwolf.py` - role display methods

**Improvements**:
- Use richer embeds for role reveals
- Add role-specific emojis consistently
- Show only selected roles in game setup message

## Testing Checklist

- [ ] User with no special roles can start game (villagers + werewolves only)
- [ ] User with special roles sees role selection UI
- [ ] Toggle buttons work correctly (select/deselect)
- [ ] Starting game with selected roles assigns only those roles
- [ ] Role distribution respects player count limits
- [ ] Game timeline flows correctly with custom role sets
- [ ] All role abilities work as expected
- [ ] DMs are sent correctly for selected roles
- [ ] Game can complete successfully with various role combinations

## Risks & Considerations

1. **Breaking Changes**: This modifies core game logic - must be tested thoroughly
2. **Edge Cases**: What if all special roles are deselected? (Answer: villagers vs werewolves)
3. **Balance**: Some role combinations might make game unbalanced
4. **UI Complexity**: Discord button limits (25 buttons max per message)
5. **Backwards Compatibility**: Existing games in progress shouldn't break

## Recommendation

This is a **major feature rework** that requires:
- Dedicated testing environment
- Multiple test games with different configurations
- User feedback on balance and usability
- Potential rollback plan

**Suggested Approach**:
1. Implement in a feature branch
2. Deploy to test server
3. Run multiple test games
4. Gather feedback
5. Iterate on design
6. Deploy to production

**Estimated Development Time**: 4-6 hours for full implementation and testing

**Priority**: Medium - Nice to have but not critical for bot functionality
