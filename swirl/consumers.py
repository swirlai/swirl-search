import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from swirl.models import Result, Search
from swirl.processors import *
import asyncio

import logging
logger = logging.getLogger(__name__)

instances = {}

class Consumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            if not self.scope['user'].is_authenticated or not self.scope['search_id']:
                await self.close(code=403)

            await self.accept()
        except Exception as e:
            await self.close(code=403) 
            

    @database_sync_to_async
    def get_rag_result(self, search_id, rag_query_items):
        isRagItemsUpdated = False
        try:
            rag_result = Result.objects.get(search_id=search_id, searchprovider='ChatGPT')
            isRagItemsUpdated = True
            isRagItemsUpdated = not(set(rag_result.json_results[0]['rag_query_items']) == set(rag_query_items))
        except:
            pass
        try:
            rag_result = Result.objects.get(search_id=search_id, searchprovider='ChatGPT')
            isRagItemsUpdated = not(set(rag_result.json_results[0]['rag_query_items']) == set(rag_query_items))
            if rag_result and not isRagItemsUpdated:
                if rag_result.json_results[0]['body'][0]:
                    return rag_result.json_results[0]['body'][0]
                return False
        except:
            pass
        rag_processor = RAGPostResultProcessor(search_id=search_id, request_id='', should_get_results=True, rag_query_items=rag_query_items)
        instances[search_id] = rag_processor
        if rag_processor.validate():
            result = rag_processor.process(should_return=True)
            try:
                if search_id in instances:
                    del instances[search_id]
                return result.json_results[0]['body'][0]
            except:
                if search_id in instances:
                    del instances[search_id]
                return False
                
    async def process_rag(self, search_id, rag_query_items):
        result = await self.get_rag_result(search_id, rag_query_items)
        if result:
            await self.send(text_data=json.dumps({
                'message': result
            }))
        else:
            await self.send(text_data=json.dumps({
                'message': 'No data'
            }))

    def stop_rag_processor(self, search_id):
        if search_id in instances:
            instance = instances[search_id]
            if instance.tasks:
                for task in instance.tasks:
                    task.revoke()
            instance.stop_processing()

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get('message', '')
        search_id = str(self.scope['search_id'])
        if message == 'stop':
            self.stop_rag_processor(search_id=search_id)
        else:
            try:
                rag_query_items = self.scope['rag_query_items']
                asyncio.create_task(self.process_rag(search_id, rag_query_items))
            except:
                await self.send(text_data=json.dumps({
                    'message': 'No data'
                }))