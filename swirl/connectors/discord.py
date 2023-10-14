import asyncio

import discord
from django.conf import settings

from swirl.connectors.connector import Connector
from swirl.connectors.mappings import *

logger = get_task_logger(__name__)
path.append(swirl_setdir())
environ.setdefault('DJANGO_SETTINGS_MODULE', 'swirl_server.settings')
django.setup()


class Discord(Connector):
    type = "Discord"

    def __init__(self, provider_id, search_id, update, request_id=''):
        self.client = discord.Client(intents=discord.Intents.all())
        super().__init__(provider_id, search_id, update, request_id)
        self.client.event(self.on_ready)

    async def on_ready(self):
        await self.client.wait_until_ready()
        await asyncio.sleep(2)
        #replace your channel id here
        channel_id = 718114919056146528
        target_channel = self.client.get_channel(channel_id)
        if target_channel is None:
            print('Channel not found')
            self.status = "ERR_CHANNEL_NOT_FOUND"
            return

        print('Connected')
        messages_data = []
        async for message in target_channel.history(limit=5):
            messages_data.append({
                "author": message.author.name,
                "body": message.content,
                "title": "discord"
            })
        self.response = messages_data
        logger.info(f"data={messages_data}")
        await self.client.close()

    def execute_search(self, session=None):
        if self.provider.credentials:
            token = self.provider.credentials
        else:
            if getattr(settings, 'DISCORD_BOT_TOKEN', None):
                token = settings.DISCORD_BOT_TOKEN
                logger.info(f"token={token}")
            else:
                self.status = "ERR_NO_CREDENTIALS"
                return
        try:
            self.client.run(token)
        except Exception as e:
            logger.error(f"Failed to start client: {e}")
            self.status = "ERR_CLIENT_START_FAILURE"

    def normalize_response(self):

        logger.debug(f"{self}: normalize_response()")
        self.results = self.response
        return
