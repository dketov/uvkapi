#!/usr/bin/env micropython

import sys

from time import time, sleep
import ujson as json

import aiohttp
import asyncio

token = "vk1.a.HlP........FnQ" # group access token, see https://dev.vk.com/ru/api/access-token/community-token/in-community-settings
gid = 235160406 # group id
uid = 837559 # user id who is allowed to talk to the bot

def rid():
  return int(time()*1000000) % 2**32

from vk import API, LongPollServer, OAuth2

async def main():
  api = API(token)
  lps = LongPollServer(api, group_id=gid)

  if not await lps.refresh():
    return

  print("lps.server", lps.server)
  while True:
    print(".")
    for u in await lps.poll():
      msg = u.object.message
      if msg.peer_id != uid:
        continue
      if not msg.text.startswith("/"):
        continue
      command, *args = msg.text.lstrip("/").split()
      try:
        cmd = __import__(command)
      except ImportError:
        continue
      try:
        answer = await cmd.answer(*args)      
      except TypeError:
        continue

      m = await api.messages.send(
             random_id=rid(), message=answer,
             peer_id=msg.peer_id, group_id=gid
          )
      print(m)

asyncio.run(main())
