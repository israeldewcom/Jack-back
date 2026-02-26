import asyncio
from aiokafka import AIOKafkaConsumer
import json
import os
from .processor import process_telemetry
from ..observability.logging import logger

class TelemetryConsumer:
    def __init__(self, max_concurrent=10):
        self.consumer = AIOKafkaConsumer(
            'telemetry',
            bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092'),
            group_id='citp-processor',
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        self.semaphore = asyncio.Semaphore(max_concurrent)

    async def start(self):
        await self.consumer.start()
        asyncio.create_task(self._run())

    async def _run(self):
        try:
            async for msg in self.consumer:
                async with self.semaphore:
                    asyncio.create_task(process_telemetry(msg.value))
        finally:
            await self.consumer.stop()
