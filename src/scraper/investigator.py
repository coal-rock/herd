import asyncio
from dataclasses import dataclass
from collections.abc import AsyncIterator
from multiprocessing import connection
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
    connector: aiohttp.TCPConnector
    parallel_requests: int
    hosts: list[Host]

    def __init__(self, hosts: list[Host], parallel_requests: int) -> None:
        self.connector = aiohttp.TCPConnector(limit=0)
        self.parallel_requests = parallel_requests
        self.hosts = hosts
        pass

    async def start(self):
        semaphore = asyncio.Semaphore(self.parallel_requests)
        session = aiohttp.ClientSession(connector=self.connector)
        ollama_hosts: list[OllamaHost] = []

        async def get(host: Host):
            async with semaphore:
                models: list[OllamaModel] = []
                version: str

                try:
                    async with session.get(
                        f"http://{host.ip}:{host.port}/api/tags", ssl=False
                    ) as response:
                        response = await response.json()  # pyright:ignore[reportAny]

                        for model in response["models"]:  # pyright:ignore[reportAny]
                            model = from_dict(
                                data_class=OllamaModel,
                                data=json.loads(model),  # pyright:ignore[reportAny]
                            )

                            models.append(model)

                    async with session.get(
                        f"http://{host.ip}:{host.port}/api/version", ssl=False
                    ) as response:
                        response = await response.json()  # pyright:ignore[reportAny]
                        version = response["version"]  # pyright:ignore[reportAny]

                    ollama_hosts.append(
                        OllamaHost(
                            ip=host.ip,
                            port=host.port,
                            models=models,
                            version=version,
                            last_seen=time.time(),
                        )
                    )
                except Exception as _:
                    pass

        _ = await asyncio.gather(*(get(host) for host in self.hosts))
