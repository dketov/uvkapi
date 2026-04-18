import aiohttp
import asyncio

url = "https://api.myip.com"

async def answer(*args):
  async with aiohttp.ClientSession() as session:
    async with session.get(url) as response:
      return await response.text()

if __name__ == "__main__":
  print(asyncio.run(answer()))
