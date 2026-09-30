import json
import logging
import threading
import queue
import time
from typing import List, Dict, Any, Optional
import urllib.request
import urllib.error

logger = logging.getLogger("arp.exporter")

class TelemetryExporter:
    def __init__(
        self,
        endpoint: str = "http://localhost:8000/api/v1/ingest/spans",
        api_key: Optional[str] = None,
        project_id: str = "proj_default_production",
        environment: str = "production",
        batch_size: int = 50,
        flush_interval_sec: float = 1.0,
        max_queue_size: int = 10000,
        fail_closed: bool = False,
        direct_handler: Optional[Any] = None
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.project_id = project_id
        self.environment = environment
        self.batch_size = batch_size
        self.flush_interval_sec = flush_interval_sec
        self.fail_closed = fail_closed
        self.direct_handler = direct_handler
        
        self.queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

    def enqueue_span(self, span_dict: Dict[str, Any]) -> None:
        try:
            self.queue.put_nowait(span_dict)
        except queue.Full:
            logger.warning("ARP Telemetry queue full, dropping span to preserve application performance")
            if self.fail_closed:
                raise RuntimeError("ARP Telemetry queue full")

    def _worker_loop(self) -> None:
        while not self._stop_event.is_set():
            items = []
            try:
                # Wait for at least one item
                item = self.queue.get(timeout=self.flush_interval_sec)
                items.append(item)
                # Drain queue up to batch_size
                while len(items) < self.batch_size:
                    try:
                        items.append(self.queue.get_nowait())
                    except queue.Empty:
                        break
            except queue.Empty:
                continue

            if items:
                self._send_batch(items)
                for _ in items:
                    self.queue.task_done()

    def _send_batch(self, items: List[Dict[str, Any]]) -> bool:
        if not items:
            return True
        if self.direct_handler:
            try:
                self.direct_handler(items)
                return True
            except Exception as e:
                logger.warning(f"Direct telemetry handler failed: {e}")
                return False

        payload = json.dumps({"spans": items}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "X-Project-Id": self.project_id,
            "X-Environment": self.environment
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        req = urllib.request.Request(self.endpoint, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                if 200 <= resp.status < 300:
                    return True
                logger.warning(f"ARP Ingestion returned non-2xx status: {resp.status}")
                return False
        except Exception as e:
            logger.warning(f"Telemetry export failed: {e}")
            if self.fail_closed:
                raise
            return False

    def flush(self, timeout: float = 5.0) -> None:
        start = time.time()
        while not self.queue.empty() and (time.time() - start < timeout):
            items = []
            while len(items) < self.batch_size:
                try:
                    items.append(self.queue.get_nowait())
                except queue.Empty:
                    break
            if items:
                self._send_batch(items)
                for _ in items:
                    self.queue.task_done()
            time.sleep(0.05)

    def shutdown(self) -> None:
        self.flush()
        self._stop_event.set()
        self._worker_thread.join(timeout=2.0)
