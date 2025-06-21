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

    def __init__(
        self, range: str = "0.0.0.0/0", port: int = 11434, max_rate: int = 10000
    ):
        self.range = range
        self.port = port
        self.max_rate = max_rate

    async def scan(self) -> AsyncIterator[Host]:
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
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError as e:
            raise MasscanNotFound from e

        while True:
            try:
                if process.stdout is not None:
                    if process.stdout.at_eof():
                        break

                    try:
                        line = await process.stdout.readuntil(separator=(b"\r", b"\n"))
                    except asyncio.IncompleteReadError as e:
                        line = e.partial

                    line = line.decode()

                    if "FAIL: permission denied" in line:
                        raise LackingRequiredPermissions

                    if "FAIL:" in line:
                        raise MasscanGeneric(line.split("FAIL: ")[1])

                    if line.strip().startswith("open"):
                        line_parts = line.strip().split(" ")

                        port = int(line_parts[2])
                        ip = line_parts[3]

                        try:
                            timestamp = int(line_parts[4])
                        except ValueError:
                            first = line_parts[4].split("rate")[0]

                            new_line = await process.stdout.readuntil(
                                separator=(b"\r", b"\n")
                            )

                            while "rate" in new_line.decode():
                                try:
                                    new_line = await process.stdout.readuntil(
                                        separator=(b"\r", b"\n")
                                    )
                                except asyncio.IncompleteReadError as e:
                                    new_line = e.partial

                            timestamp = int(first + new_line.decode())

                        yield Host(ip, port, timestamp)

                else:
                    break
            except Exception:
                continue


class MasscanNotFound(Exception):
    pass


class MasscanGeneric(Exception):
    pass


class LackingRequiredPermissions(Exception):
    pass
