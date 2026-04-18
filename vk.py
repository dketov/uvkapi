from time import time

import aiohttp
import asyncio

def rid():
  return int(time()*1000000) % 2**32

class JSON:
  def __init__(self, data):
    self.data = data

  @staticmethod
  def wrap(obj):
    if isinstance(obj, dict):
      return JSON(obj)
    if isinstance(obj, list):
      return map(JSON.wrap, obj)
    return obj

  def __getattr__(self, attr):
    return JSON.wrap(
      self.data.get(attr)
    )

  def __str__(self):
    return str(self.data)

class OAuth2:
  auth1url = "https://id.vk.ru/authorize"
  auth2url = "https://id.vk.ru/oauth2/auth"

  def __init__(self, appid):
    self.appid = appid

  def get_url(self, base, params):
    qs = "&".join(f"{n}={v}" for n, v in params.items())
    return f"{base}?{qs}"

  def get_code_url(self, scope):
    from pkce import S256
    self.s256 = S256()
    return self.get_url(self.auth1url, {
     "response_type": "code",
     "client_id": self.appid,
     "code_challenge": self.s256.code_challenge,
     "code_challenge_method": self.s256.name,
     "redirect_uri": "https://oauth.vk.com/blank.html",
     "scope": scope, "prompt": "consent"
    })

  async def get_tokens(self, url):
    _, qs = url.split("?")
    params = dict(kv.split("=") for kv in qs.split("&"))

    params= {
     "grant_type": "authorization_code",
     "client_id": self.appid,
     "device_id": params["device_id"],
     "code": params["code"],
     "code_verifier": self.s256.code_verifier,
     "redirect_uri": "https://oauth.vk.com/blank.html"
    }

    fd = "&".join(f"{n}={v}" for n, v in params.items())
    async with aiohttp.ClientSession() as session:
      async with session.post(self.auth2url,
                              headers={"Content-Type": "application/x-www-form-urlencoded"},
                              data=fd) as response:
        if response.status != 200:
          return
        resp = await response.json()
        return resp["access_token"], resp["refresh_token"]

class API:
  class Error(Exception):
    pass

  server = "https://api.vk.com"
  version = "5.199"

  def __init__(self, token):
    self.token = token

  def __getattr__(self, name):
    return API.Object(self, name)

  class Object:
    def __init__(self, api, name):
      self.api = api
      self.name = name

    def __getattr__(self, name):
      return API.Method(self.api, f"{self.name}.{name}")
 
  class Method:
    def __init__(self, api, name):
      self.api = api
      self.name = name

    @property
    def url(self):
      return f"{self.api.server}/method/{self.name}?v={self.api.version}&access_token={self.api.token}"

    async def __call__(self, **params):
      fd = "&".join(f"{n}={v}" for n, v in params.items())

      async with aiohttp.ClientSession() as session:
        async with session.post(self.url,
                                headers={"Content-Type": "application/x-www-form-urlencoded"},
                                data=fd) as response:
          if response.status == 200:
            return JSON(await response.json())

class LongPollServer:
  def __init__(self, api, **kwargs):
    self.api = api
    self.kwargs = kwargs
    self.to = 10

  async def refresh(self):
    desc = await self.api.groups.getLongPollServer(**self.kwargs)
    if desc.error:
      raise API.Error(desc.error)
    self.server = desc.response.server
    self.key = desc.response.key
    self.ts = desc.response.ts
    return self.server

  @property
  def url(self):
    return f"{self.server}?act=a_check&key={self.key}&ts={self.ts}&wait={self.to}"

  async def poll(self):
    async with aiohttp.ClientSession() as session:
      async with session.get(self.url) as response:
        if response.status != 200:
	  return
        resp = JSON(await response.json())
      if resp.failed and resp.failed > 1:
        await self.refresh()
        return []
      self.ts = resp.ts
      return resp.updates
