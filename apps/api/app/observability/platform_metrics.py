import time
from typing import Dict, Any, List
from datetime import datetime

class PlatformObservability:
    def __init__(self):
        self.start_time = datetime.utcnow()
        self.total_spans_ingested = 0
        self.total_batches_processed = 0
        self.total_queries_served = 0
        self.ingestion_latencies_ms: List[float] = []
        self.query_latencies_ms: List[float] = []
        self.platform_errors_count = 0

    def record_ingestion(self, span_count: int, latency_ms: float):
        self.total_spans_ingested += span_count
        self.total_batches_processed += 1
        self.ingestion_latencies_ms.append(latency_ms)
        if len(self.ingestion_latencies_ms) > 1000:
            self.ingestion_latencies_ms.pop(0)

    def record_query(self, latency_ms: float):
        self.total_queries_served += 1
        self.query_latencies_ms.append(latency_ms)
        if len(self.query_latencies_ms) > 1000:
            self.query_latencies_ms.pop(0)

    def record_error(self):
        self.platform_errors_count += 1

    def get_metrics(self) -> Dict[str, Any]:
        uptime_seconds = (datetime.utcnow() - self.start_time).total_seconds()
        
        avg_ingest = round(sum(self.ingestion_latencies_ms) / len(self.ingestion_latencies_ms), 2) if self.ingestion_latencies_ms else 0.0
        sorted_ingest = sorted(self.ingestion_latencies_ms)
        p95_ingest = round(sorted_ingest[int(len(sorted_ingest) * 0.95)], 2) if sorted_ingest else 0.0

        avg_query = round(sum(self.query_latencies_ms) / len(self.query_latencies_ms), 2) if self.query_latencies_ms else 0.0
        sorted_query = sorted(self.query_latencies_ms)
        p95_query = round(sorted_query[int(len(sorted_query) * 0.95)], 2) if sorted_query else 0.0

        throughput = round(self.total_spans_ingested / max(uptime_seconds, 1.0), 2)

        return {
            "uptime_seconds": round(uptime_seconds, 1),
            "total_spans_ingested": self.total_spans_ingested,
            "total_batches_processed": self.total_batches_processed,
            "total_queries_served": self.total_queries_served,
            "ingestion_throughput_spans_per_sec": throughput,
            "ingestion_latency": {
                "avg_ms": avg_ingest,
                "p95_ms": p95_ingest,
                "samples": len(self.ingestion_latencies_ms)
            },
            "query_latency": {
                "avg_ms": avg_query,
                "p95_ms": p95_query,
                "samples": len(self.query_latencies_ms)
            },
            "platform_errors_count": self.platform_errors_count,
            "status": "healthy"
        }

platform_metrics = PlatformObservability()
