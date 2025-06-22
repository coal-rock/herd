from scraper import investigator
from scraper.investigator import Investigator
from scraper.scanner import Host, Scanner
import asyncio


async def main():
    hosts: list[Host] = []

    scanner = Scanner("0.0.0.0/0", port=22, max_rate=1000, limit=10)

    async for host in scanner.scan():
        hosts.append(host)

    investigator = Investigator(hosts, 1000)
    await investigator.start()


asyncio.run(main())
