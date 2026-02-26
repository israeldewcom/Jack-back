"""
Kafka consumer for telemetry events with concurrency control.
"""
import asyncio
from aiokafka import AIOKafkaConsumer
import json
import os
from .processor import process_telemetry
from ..observability.logging import logger

class TelemetryConsumer:
    def __init__(self, max_concurrent=10):
        self.consumer = AIOKafkaConsumer(
            os.getenv("KAFKA_TOPIC", "telemetry"),
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            group_id=os.getenv("KAFKA_GROUP_ID", "citp-processor"),
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            auto_offset_reset="earliest",
            enable_auto_commit=False,  # we commit after processing
            max_poll_records=int(os.getenv("KAFKA_MAX_POLL_RECORDS", "100"))
        )
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.running = True

    async def start(self):
        await self.consumer.start()
        logger.info("Kafka consumer started")
        try:
            async for msg in self.consumer:
                if not self.running:
                    break
                async with self.semaphore:
                    # Process without blocking the consumer loop
                    asyncio.create_task(self._process_with_commit(msg))
        finally:
            await self.consumer.stop()

    async def _process_with_commit(self, msg):
        try:
            await process_telemetry(msg.value)
            # Commit after successful processing
            await self.consumer.commit()
        except Exception as e:
            logger.exception(f"Error processing message {msg.offset}, skipping commit")
            # In production, you might send to DLQ

    async def stop(self):
        self.running = False
