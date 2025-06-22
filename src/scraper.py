from scraper.investigator import Investigator
from scraper.scanner import Host, Scanner
import asyncio
import multiprocessing


async def main():
    scanner = Scanner("0.0.0.0/0", port=22, max_rate=1000)
    investigator = Investigator()
    investigator.start()

    async for host in scanner.scan():
        await investigator.add_host(Host("127.0.0.1", 22, 69))

    await asyncio.sleep(10000000)


asyncio.run(main())
