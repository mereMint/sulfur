import asyncio
import discord
from modules.db_helpers import get_owned_channel, add_managed_channel, remove_managed_channel, get_managed_channel_config, update_managed_channel_config, log_temp_vc_creation

# --- NEW: Import structured logging ---
from modules.logger_utils import voice_logger as logger

# --- NEW: Anti-race-condition lock ---
creating_channel_for = set()

async def handle_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState, config: dict):
    """
    Handles the logic for "Join to Create" voice channels.
    """
    join_to_create_channel_name = config['modules']['voice_manager']['join_to_create_channel_name']
    # --- Handle channel creation ---
    if after.channel and after.channel.name == join_to_create_channel_name:
        # --- CRITICAL: Acquire lock IMMEDIATELY to prevent race conditions ---
        if member.id in creating_channel_for:
            logger.debug(f"Ignoring duplicate join event for {member.display_name} - creation already in progress")
            return

        # Acquire lock before ANY async operations
        creating_channel_for.add(member.id)

        try:
            # --- REFACTORED: Prevent creating multiple channels by checking the database ---
            owned_channel_id = await get_owned_channel(member.id, member.guild.id)
            if owned_channel_id:
                try:
                    owned_channel = member.guild.get_channel(owned_channel_id)
                    if owned_channel:
                        # Move them to their existing channel instead of creating a new one
                        await member.move_to(owned_channel, reason="User already owns a channel.")
                        logger.debug(f"Moved {member.display_name} to existing channel {owned_channel.name}")
                        return
                    else:
                        # The channel was deleted but the database still has a reference
                        # Clean up the stale reference and allow creation to proceed
                        logger.warning(f"Stale channel reference for {member.display_name}: channel {owned_channel_id} doesn't exist")
                        await remove_managed_channel(owned_channel_id, keep_owner_record=True)
                        print(f"Cleaned up stale channel reference for {member.display_name}")
                        # Don't return - continue with channel creation
                except (discord.Forbidden, discord.HTTPException) as e:
                    logger.error(f"Error checking owned channel for {member.display_name}: {e}")
                    # Return here to prevent duplicate channel creation on error
                    return

            guild = member.guild
            # --- NEW: Use configured category name, fallback to current category ---
            category = discord.utils.get(guild.categories, name=config['modules']['voice_manager']['dynamic_channel_category_name'])
            if not category:
                # Fallback to the category of the "Join to Create" channel if the configured one doesn't exist
                category = after.channel.category

            # --- NEW: Fetch last used config for the user ---
            last_config = await get_managed_channel_config((member.id, member.guild.id), by_owner=True)
            if last_config and last_config.get('channel_name'):
                new_channel_name = last_config['channel_name']
                user_limit = last_config.get('user_limit', 0)
            else:
                new_channel_name = f"🔊 {member.display_name}'s Channel"
                user_limit = 0

            # SAFETY CHECK: Ensure user is STILL in the join-to-create channel before creation
            if not member.voice or member.voice.channel != after.channel:
                logger.debug(f"{member.display_name} left join channel before creation started; aborting create.")
                return

            # Create the voice channel
            new_channel = await guild.create_voice_channel(
                name=new_channel_name,
                category=category,
                user_limit=user_limit,
                reason=f"Created for {member.display_name}"
            )

            # --- FIX: Verify user didn't leave during channel creation ---
            if not member.voice or member.voice.channel != after.channel:
                logger.debug(f"{member.display_name} left join channel during creation; cleaning up {new_channel.id}")
                try:
                    await new_channel.delete(reason="User left before channel was ready")
                except Exception:
                    pass
                return

            # --- REORDERED: Add to DB BEFORE moving the user to prevent race condition ---
            await add_managed_channel(new_channel.id, member.id, guild.id)
            # --- NEW: Log the creation for Wrapped stats ---
            await log_temp_vc_creation(member.id, guild.id, discord.utils.utcnow())

            logger.info(f"Created managed voice channel: {new_channel.name} ({new_channel.id}) for {member.display_name}")
            print(f"Created managed voice channel: {new_channel.name} ({new_channel.id})")

            # Move the user to their new channel immediately (no delay)
            try:
                # --- FIX: Final check before move ---
                if not member.voice or member.voice.channel != after.channel:
                    logger.debug(f"{member.display_name} left join channel before move; cleaning up {new_channel.id}")
                    await new_channel.delete(reason="User left before being moved")
                    await remove_managed_channel(new_channel.id, keep_owner_record=True)
                    return

                await member.move_to(new_channel, reason="Join to Create")
                # --- NEW: Unmute and undeafen the user after moving them ---
                await member.edit(mute=False, deafen=False, reason="User moved to their new channel")
                logger.debug(f"Successfully moved {member.display_name} to {new_channel.name}")
            except discord.HTTPException as move_error:
                # This can happen if the user disconnects while the channel is being created.
                logger.warning(f"Failed to move {member.display_name}: {move_error}")
                print(f"Failed to move {member.display_name} to their new channel (they may have disconnected).")
                # --- FIX: Clean up the orphaned channel immediately ---
                try:
                    await new_channel.delete(reason="User disconnected before being moved.")
                    await remove_managed_channel(new_channel.id, keep_owner_record=True)
                    print(f"Cleaned up orphaned channel '{new_channel.name}' immediately.")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup orphaned channel: {cleanup_error}")

        except discord.Forbidden:
            logger.error(f"Bot lacks permissions to create channels or move members in '{member.guild.name}'")
            print(f"Error: Bot lacks permissions to create channels or move members in '{member.guild.name}'.")
        except Exception as e:
            logger.error(f"Error during channel creation: {e}", exc_info=True)
            print(f"An error occurred during channel creation: {e}")
        finally:
            # --- CRITICAL: Always release lock ---
            if member.id in creating_channel_for:
                creating_channel_for.discard(member.id)
            return  # Exit early to prevent further processing

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
            # --- FIX: Get the current channel object from the guild, not fetch (faster) ---
            # The 'before.channel' object is a snapshot. We need the *current* state of the channel
            # to ensure our checks and actions are based on the most up-to-date information.
            fresh_channel = member.guild.get_channel(before.channel.id)
            
            # If channel was already deleted, clean up DB
            if not fresh_channel:
                logger.debug(f"Channel {before.channel.id} already deleted, cleaning up DB")
                await remove_managed_channel(before.channel.id, keep_owner_record=True)
                return

            # Check if the channel is NOW empty
            if len(fresh_channel.members) == 0:
                # Save the current name and limit for the owner by passing their ID
                await update_managed_channel_config((channel_config['owner_id'], member.guild.id), by_owner=True, name=fresh_channel.name, limit=fresh_channel.user_limit)
                
                # --- FIX: Delete empty channels immediately, no grace period needed ---
                # The grace period was causing orphaned channels when users disconnected quickly.
                # Since we now have better race condition handling during creation,
                # we can safely delete empty channels immediately.
                try:
                    await fresh_channel.delete(reason="Channel is empty")
                    # We keep the record in the DB for the user's settings by setting channel_id to NULL
                    await remove_managed_channel(before.channel.id, keep_owner_record=True)
                    logger.info(f"Deleted empty managed voice channel: {fresh_channel.name} ({fresh_channel.id})")
                    print(f"Deleted empty managed voice channel: {fresh_channel.name} ({fresh_channel.id})")
                except (discord.NotFound, discord.Forbidden) as e:
                    logger.warning(f"Error deleting channel {fresh_channel.name}: {e}")
                    print(f"Error deleting channel {fresh_channel.name}: {e}")
                    # Still remove from DB to prevent orphans
                    await remove_managed_channel(before.channel.id, keep_owner_record=True)