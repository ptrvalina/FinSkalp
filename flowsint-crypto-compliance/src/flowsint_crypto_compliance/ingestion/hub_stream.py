"""Optional Redpanda/Kafka ingest for continuous bank hub feeds."""

from __future__ import annotations

import json
import os
from typing import Any, Callable, Iterator

from flowsint_crypto_compliance.schemas.hub import validate_bank_feed_batch


class HubStreamConsumer:
    """
    Consumes regulator-hub batch messages from Kafka/Redpanda when configured.

    Set KAFKA_BOOTSTRAP_SERVERS and REGULATOR_HUB_TOPIC to enable.
    """

    def __init__(
        self,
        *,
        bootstrap_servers: str,
        topic: str,
        group_id: str = "flowsint-compliance-hub",
    ) -> None:
        self._bootstrap = bootstrap_servers
        self._topic = topic
        self._group_id = group_id

    @classmethod
    def from_env(cls) -> HubStreamConsumer | None:
        bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS") or os.getenv("REDPANDA_BROKERS")
        topic = os.getenv("REGULATOR_HUB_TOPIC")
        if not bootstrap or not topic:
            return None
        return cls(bootstrap_servers=bootstrap, topic=topic)

    def iter_batches(self, *, max_messages: int = 100) -> Iterator[dict[str, Any]]:
        try:
            from kafka import KafkaConsumer
        except ImportError as exc:
            raise RuntimeError("kafka-python required for hub stream ingest") from exc

        consumer = KafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap.split(","),
            group_id=self._group_id,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        count = 0
        try:
            for message in consumer:
                batch = message.value
                if isinstance(batch, dict) and "feeds" in batch:
                    validate_bank_feed_batch(batch)
                    yield batch
                    count += 1
                    if count >= max_messages:
                        break
        finally:
            consumer.close()

    def poll_once(self, handler: Callable[[dict[str, Any]], None], *, max_messages: int = 10) -> int:
        processed = 0
        for batch in self.iter_batches(max_messages=max_messages):
            handler(batch)
            processed += 1
        return processed
