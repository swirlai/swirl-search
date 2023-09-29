import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from swirl.models import Result, Search
from swirl.processors import *
import time


class Consumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            if not self.scope['user'].is_authenticated or not self.scope['search_id']:
                await self.close(code=403)

            self.room_group_name = f"connection_{self.scope['search_id']}"

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
        except Exception as e:
            await self.close(code=403) 
            

    async def disconnect(self, code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    @database_sync_to_async
    def get_rag_result(self, search_id):
        search = Search.objects.get(id=search_id)
        isRagIncluded = "RAGPostResultProcessor" in search.post_result_processors
        if isRagIncluded:
            while 1:
                try:
                    rag_result = Result.objects.get(search_id=search_id, searchprovider='ChatGPT')
                    if rag_result.json_results[0]['body'][0]:
                        return rag_result.json_results[0]['body'][0]
                    time.sleep(1)
                    continue
                except:
                    time.sleep(1)
                    continue
        else:
            try:
                rag_result = Result.objects.get(search_id=search_id, searchprovider='ChatGPT')
                if rag_result.json_results[0]['body'][0]:
                    return rag_result.json_results[0]['body'][0]
            except: 
                pass
            rag_processor = RAGPostResultProcessor(search_id=search_id, request_id='', is_socket_logic=True)
            if rag_processor.validate():
                result = rag_processor.process(should_return=True)
                try:
                    return result.json_results[0]['body'][0]
                except:
                    return False
                


    async def receive(self, text_data):
        result = await self.get_rag_result(self.scope['search_id'])
        if result:
            await self.send(text_data=json.dumps({
                'message': result
            }))
        else:
            await self.send(text_data=json.dumps({
                'message': 'No data'
            }))