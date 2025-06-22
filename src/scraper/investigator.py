import asyncio
from dataclasses import dataclass
from collections.abc import AsyncIterator
import aiohttp
from scraper.scanner import Host
import json
from dacite import from_dict
import time


@dataclass
class OllamaModelDetails:
    parent_model: str
    format: str
    family: str
    families: list[str]
    parameter_size: str
    quantization_level: str


@dataclass
class OllamaModel:
    name: str
    model: str
    modified_at: str
    size: int
    digest: str
    details: OllamaModelDetails


@dataclass
class OllamaHost:
    ip: str
    port: int
    version: str
    models: list[OllamaModel]
    last_seen: float


class Investigator:
    input_queue: asyncio.Queue[Host]
    output_queue: asyncio.Queue[OllamaHost]

    task_group: asyncio.TaskGroup | None
    client: aiohttp.ClientSession | None
    worker_task: asyncio.Task[None] | None

    running: bool

    def __init__(self) -> None:
        self.task_group = None

        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        self.running = False

        self.client = None
        self.worker_task = None

    def start(self):
        """
        Creates an aiohttp instance and instantiates worker task
        """
        self.running = True
        self.client = aiohttp.ClientSession()
        self.task_group = asyncio.TaskGroup()
        self.worker_task = asyncio.create_task(self.worker())

    async def stop(self):
        self.running = False

        if self.worker_task is not None:
            await self.worker_task

        if self.task_group is not None:
            await self.task_group.__aexit__(None, None, None)

        if self.client is not None:
            await self.client.close()

    async def iter(self) -> AsyncIterator[OllamaHost]:
        while not self.output_queue.empty():
            yield await self.output_queue.get()

    async def add_host(self, host: Host):
        await self.input_queue.put(host)

    async def fetch(self, host: Host):
        if self.client is None:
            return

        try:
            res = await self.client.get(f"http://{host.ip}:{host.port}/api/tags")
            res = await res.json()  # pyright:ignore[reportAny]
            models: list[OllamaModel] = []

            for model in res["models"]:  # pyright:ignore[reportAny]
                model = from_dict(
                    data_class=OllamaModel,
                    data=json.loads(model),  # pyright:ignore[reportAny]
                )

                models.append(model)

            res = await self.client.get(f"http://{host.ip}:{host.port}/api/version")
            res = await res.json()  # pyright:ignore[reportAny]
            version = res["version"]  # pyright:ignore[reportAny]

            await self.output_queue.put(
                OllamaHost(
                    ip=host.ip,
                    port=host.port,
                    models=models,
                    version=version,  # pyright:ignore[reportAny]
                    last_seen=time.time(),
                )
            )

        except Exception as e:
            pass
            # print(f"INVESTIGATION ERROR: {host} | {e}")

    async def worker(self):
        if self.task_group is None:
            return

        _ = await self.task_group.__aenter__()

        while self.running:
            try:
                host = await asyncio.wait_for(self.input_queue.get(), timeout=1.0)
                _ = self.task_group.create_task(self.fetch(host))
            except asyncio.TimeoutError:
                continue
