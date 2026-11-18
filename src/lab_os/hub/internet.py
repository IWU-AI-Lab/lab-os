"""Is there internet? Checked in the background (~every 30 s) by opening a TCP connection to a
couple of well-known addresses (IP numbers, so no DNS needed). Nothing is sent."""

import asyncio
import logging
import time

log = logging.getLogger(__name__)

TARGETS = (("1.1.1.1", 443), ("8.8.8.8", 443))
EVERY_S = 30.0
TIMEOUT_S = 3.0
RETRY_S = 2.0  # after a miss while online


async def _reachable(host: str, port: int) -> bool:
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), TIMEOUT_S)
    except (OSError, TimeoutError):
        return False
    writer.close()
    return True


async def check_once(targets=TARGETS) -> bool:
    results = await asyncio.gather(*(_reachable(h, p) for h, p in targets))
    return any(results)


class InternetCheck:
    """`online` is None until the first check finishes, then True/False."""

    def __init__(self, every_s: float = EVERY_S, targets=TARGETS):
        self.every_s = every_s
        self.targets = targets
        self.online: bool | None = None
        self.checked_at: float | None = None

    async def run(self) -> None:
        while True:
            await self.step()
            await asyncio.sleep(self.every_s)

    async def step(self) -> bool:
        """One check (and, after a miss while online, one more)."""
        online = await check_once(self.targets)
        if not online and self.online:
            # one miss isn't "offline" yet (quick job 32): try once more first
            await asyncio.sleep(RETRY_S)
            online = await check_once(self.targets)
        if online != self.online:
            log.info("internet: %s", "online" if online else "offline")
        self.online, self.checked_at = online, time.time()
        return online
