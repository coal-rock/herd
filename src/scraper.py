from scraper.investigator import Investigator
from scraper.scanner import Scanner
import asyncio


async def scan(investigator: Investigator):
    scanner = Scanner("0.0.0.0/0", port=11434, max_rate=1000)

    print("starting scanner")

    async for host in scanner.scan():
        print("found host")
        await investigator.add_host(host)

    print("done scanning")


async def investigate(investigator: Investigator):
    investigator.start()

    print("starting investigator")

    async for host in investigator.iter():
        print(host)

    print("done investigating")


async def main():
    investigator = Investigator()

    scanner_task = asyncio.create_task(scan(investigator))
    investigator_task = asyncio.create_task(investigate(investigator))

    _ = await asyncio.gather(
        investigator_task,
        scanner_task,
    )


asyncio.run(main())
