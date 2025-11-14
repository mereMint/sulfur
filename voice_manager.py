import asyncio
import asyncio
import discord
from db_helpers import get_owned_channel, add_managed_channel, remove_managed_channel, get_managed_channel_config, update_managed_channel_config

# --- NEW: Anti-race-condition lock ---
creating_channel_for = set()

async def handle_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState, config: dict):
    """
    Handles the logic for "Join to Create" voice channels.
    """
    join_to_create_channel_name = config['modules']['voice_manager']['join_to_create_channel_name']
    # --- Handle channel creation ---
    if after.channel and after.channel.name == join_to_create_channel_name:
        # --- REFACTORED: Prevent creating multiple channels by checking the database ---
        
        # --- NEW: Check lock to prevent race conditions ---
        if member.id in creating_channel_for:
            return # Creation is already in progress for this user, ignore this event.

        owned_channel_id = await get_owned_channel(member.id)
        if owned_channel_id:
            try:
                owned_channel = member.guild.get_channel(owned_channel_id)
                if owned_channel:
                    # Move them to their existing channel instead of creating a new one
                    await member.move_to(owned_channel, reason="User already owns a channel.")
                else:
                    # The channel was deleted but not cleaned from DB. Move them out.
                    await member.move_to(None, reason="Owned channel not found.")
            except (discord.Forbidden, discord.HTTPException):
                pass # Ignore if we can't move them
            return

        guild = member.guild
        # --- NEW: Use configured category name, fallback to current category ---
        category = discord.utils.get(guild.categories, name=config['modules']['voice_manager']['dynamic_channel_category_name'])
        if not category:
            # Fallback to the category of the "Join to Create" channel if the configured one doesn't exist
            category = after.channel.category

        # --- NEW: Acquire lock ---
        creating_channel_for.add(member.id)

        try:
            # --- NEW: Fetch last used config for the user ---
            last_config = await get_managed_channel_config(member.id, by_owner=True)
            if last_config and last_config.get('channel_name'):
                new_channel_name = last_config['channel_name']
                user_limit = last_config.get('user_limit', 0)
            else:
                new_channel_name = f"🔊 {member.display_name}'s Channel"
                user_limit = 0

            # Mute the user temporarily while we create the channel
            new_channel = await guild.create_voice_channel(
                name=new_channel_name,
                category=category,
                reason=f"Created for {member.display_name}"
            )

            # --- REORDERED: Add to DB *before* moving the user to prevent race condition ---
            await add_managed_channel(new_channel.id, member.id)
            print(f"Created managed voice channel: {new_channel.name} ({new_channel.id})")

            # --- FIX: Wait a moment before moving the user to avoid race conditions ---
            await asyncio.sleep(config['modules']['voice_manager']['creation_move_delay_ms'] / 1000.0)

            # Move the user to their new channel
            try:
                await member.move_to(new_channel, reason="Join to Create")
                # --- NEW: Unmute and undeafen the user after moving them ---
                await member.edit(mute=False, deafen=False, reason="User moved to their new channel")
            except discord.HTTPException:
                # This can happen if the user disconnects while the channel is being created.
                print(f"Failed to move {member.display_name} to their new channel (they may have disconnected).")

        except discord.Forbidden:
            print(f"Error: Bot lacks permissions to create channels or move members in '{guild.name}'.")
        except Exception as e:
            print(f"An error occurred during channel creation: {e}")
        finally:
            # --- NEW: Release lock ---
            creating_channel_for.remove(member.id)

    # --- Handle joining a private channel ---
    if after.channel:
        channel_config = await get_managed_channel_config(after.channel.id)
        # If the channel is private and the user is not on the allowed list
        if channel_config and channel_config['is_private'] and member.id not in channel_config['allowed_users']:
            try:
                # Move them back to where they were, or disconnect them if they weren't in a channel
                await member.move_to(before.channel, reason="Channel is private")
                await member.send(f"Der Channel '{after.channel.name}' ist privat. Du benötigst eine Einladung vom Besitzer.", delete_after=10)
            except (discord.Forbidden, discord.HTTPException):
                pass

    # --- Handle channel deletion ---
    if before.channel:
        # Check if the channel that was left is a managed one
        channel_config = await get_managed_channel_config(before.channel.id)
        if channel_config:
            # --- NEW: Save channel state before deleting if it's empty ---
            if not before.channel.members: # Simpler check for empty
                # Save the current name and limit for the owner
                await update_managed_channel_config(channel_config['owner_id'], name=before.channel.name, limit=before.channel.user_limit)
                
                # Check if the channel is empty and old enough to delete
                creation_grace_period = config['modules']['voice_manager']['empty_channel_delete_grace_period_seconds']
                is_old_enough_to_delete = (discord.utils.utcnow() - before.channel.created_at).total_seconds() > creation_grace_period
                if not is_old_enough_to_delete:
                    return # Don't delete a channel that was just created
                
                try:
                    await before.channel.delete(reason="Channel is empty")
                    # We keep the record in the DB for the user's settings by setting channel_id to NULL
                    await remove_managed_channel(before.channel.id, keep_owner_record=True)
                    print(f"Deleted empty managed voice channel: {before.channel.name} ({before.channel.id})")
                except (discord.NotFound, discord.Forbidden) as e:
                    print(f"Error deleting channel {before.channel.name}: {e}")
                    # Still remove from DB to prevent orphans
                    await remove_managed_channel(before.channel.id, keep_owner_record=True)