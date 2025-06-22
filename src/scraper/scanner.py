from dataclasses import dataclass
import asyncio
from collections.abc import AsyncIterator


class Database:
    """
    Contains a list of all hosts that respond to the scan

    A response does not imply that a certain host is viable,
    only that it is worth looking into
    """

    pass


@dataclass
class Host:
    ip: str
    port: int
    timestamp: int


class Scanner:
    range: str
    port: int
    max_rate: int
    limit: int

    def __init__(
        self,
        range: str = "0.0.0.0/0",
        port: int = 11434,
        max_rate: int = 10000,
        limit: int = 0,
    ):
        self.range = range
        self.port = port
        self.max_rate = max_rate
        self.limit = limit

    async def scan(self) -> AsyncIterator[Host]:
        count = 0

        try:
            process = await asyncio.create_subprocess_exec(
                "masscan",
                f"-p{self.port}",
                self.range,
                "--max-rate",
                str(self.max_rate),
                "--excludefile",
                "exclude.conf",
                "-oL",
                "-",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as e:
            raise MasscanNotFound from e

        while True:
            if count >= self.limit:
                return

            if process.stdout is None or process.stderr is None:
                return

            if process.stdout.at_eof():
                while not process.stderr.at_eof():
                    line = await process.stderr.readline()
                    line = line.decode()

                    if "FAIL: permission denied" in line:
                        raise LackingRequiredPermissions

                    # handle generic error
                    if "FAIL:" in line:
                        raise MasscanGeneric(line.split("FAIL: ")[1])

                return

            try:
                line = await process.stdout.readuntil(separator=(b"\r", b"\n"))
            except asyncio.IncompleteReadError as e:
                line = e.partial

            line = line.decode()

            if line.strip().startswith("open"):
                line_parts = line.strip().split(" ")

                port = int(line_parts[2])
                ip = line_parts[3]
                timestamp = int(line_parts[4])

                count += 1
                yield Host(ip, port, timestamp)


class MasscanNotFound(Exception):
    pass


class MasscanGeneric(Exception):
    pass


class LackingRequiredPermissions(Exception):
    pass
