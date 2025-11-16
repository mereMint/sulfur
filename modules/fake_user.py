import random
import asyncio

class FakeUser:
    """
    A mock discord.User object for creating bot players in Werwolf.
    This allows the game logic to treat bots and real players similarly.
    """
    def __init__(self, name: str):
        # Use a random negative ID to avoid collisions with real Discord user IDs.
        self.id = random.randint(-10000, -1)
        self.display_name = name
        self.name = name
        self.mention = f"**{name} (Bot)**"

    async def send(self, message: str):
        """
        Mock send method. Instead of sending a DM, it prints the role/action
        to the console for debugging purposes.
        """
        print(f"--- DM to {self.display_name} (Bot) ---\n{message}\n--------------------")
        await asyncio.sleep(0) # To make it awaitable