"""Module for minimal Midea cloud API access."""
from asyncio import Lock
from datetime import datetime
import json
import logging
import os
from secrets import token_hex, token_urlsafe
import httpx
from msmart.security import security

_LOGGER = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, message, code=None) -> None:
        super().__init__(message, code)

        self.message = message
        self.code = code

    def __str__(self):
        return f"Code: {self.code}, Message: {self.message}"


class Cloud:
    """Class for minimal Midea cloud API access."""

    # Misc constants for the API
    CLIENT_TYPE = 1  # Android
    FORMAT = 2  # JSON
    LANGUAGE = "en_US"
    APP_ID = "1010"
    SRC = "1010"
    DEVICE_ID = "c1acad8939ac0d7d"

    # Base URLs
    BASE_URL = "https://mp-prod.appsmb.com"
    BASE_URL_CHINA = "https://mp-prod.smartmidea.net"

    # Default number of request retries
    RETRIES = 3

    def __init__(self, account, password, use_china_server=False):

        self._account = account
        self._password = password

        # A session dictionary that holds the login information of the current user
        self._login_id = None
        self._session = {}
        self._access_token = ""

        self._api_lock = Lock()
        self._security = security()

        if os.getenv("USE_CHINA_SERVER", "0") == "1":
            use_china_server = True

        self._base_url = Cloud.BASE_URL_CHINA if use_china_server else Cloud.BASE_URL

        _LOGGER.info("Using Midea cloud server: %s (China: %s).",
                     self._base_url, use_china_server)

    def _timestamp(self):
        return datetime.now().strftime("%Y%m%d%H%M%S")

    def _parse_response(self, response):
        """Parse a response from the API."""

        _LOGGER.debug("API response: %s", response.text)
        body = json.loads(response.text)

        response_code = int(body["code"])
        if response_code == 0:
            return body["data"]

        raise ApiError(body["msg"], code=response_code)

    async def _post_request(self, url, headers, contents, retries=RETRIES) -> dict | None:
        """Post a request to the API."""

        async with httpx.AsyncClient() as client:
            while retries > 0:
                try:
                    # Post request and handle bad status code
                    r = await client.post(url, headers=headers, content=contents)
                    r.raise_for_status()

                    # Parse the response
                    return self._parse_response(r)
                except httpx.TimeoutException as e:
                    _LOGGER.warning("Request to %s timed out.", url)
                    retries -= 1

                    # Rethrow the exception after retries expire
                    if retries == 0:
                        raise e

    async def _api_request(self, endpoint, body) -> dict | None:
        """Make a request to the Midea cloud return the results."""

        # Encode body as JSON
        contents = json.dumps(body)
        random = token_hex(16)

        # Sign the contents and add it to the header
        sign = self._security.new_sign(contents, random)
        headers = {
            'Content-Type': 'application/json',
            "secretVersion": "1",
            "sign": sign,
            "random": random,
            "accessToken": self._access_token
        }

        # Build complete request URL
        url = f"{self._base_url}/mas/v5/app/proxy?alias={endpoint}"

        # Lock the API and post the request
        async with self._api_lock:
            return await self._post_request(url, headers, contents)

    def _build_request_body(self, data):
        """Build a request body."""

        # Set up the initial body
        body = {
            "appId": Cloud.APP_ID,
            "format": Cloud.FORMAT,
            "clientType": Cloud.CLIENT_TYPE,
            "language": Cloud.LANGUAGE,
            "src": Cloud.SRC,
            "stamp": self._timestamp(),
            "deviceId": Cloud.DEVICE_ID,
            "reqId": token_hex(16),
        }

        # Add additional fields to the body
        body.update(data)

        return body

    async def _get_login_id(self):
        """Get a login ID for the cloud account."""

        response = await self._api_request(
            "/v1/user/login/id/get",
            self._build_request_body({"loginAccount": self._account})
        )

        # Assert response is not None since we should throw on errors
        assert response is not None

        return response["loginId"]

    async def login(self, force=False):
        """Login to the cloud API."""

        # Don't login if session already exists
        if self._session and not force:
            return

        # Get a login ID if we don't have one
        if self._login_id is None:
            self._login_id = await self._get_login_id()
            _LOGGER.debug("Received loginId: %s", self._login_id)

        # Build the login data
        body = {
            "data": {
                "platform": Cloud.FORMAT,
                "deviceId": Cloud.DEVICE_ID,
            },
            "iotData": {
                "appId": Cloud.APP_ID,
                "clientType": Cloud.CLIENT_TYPE,
                "iampwd": self._security.encrypt_iam_password(self._login_id, self._password),
                "loginAccount": self._account,
                "password": self._security.encryptPassword(self._login_id, self._password),
                "pushToken": token_urlsafe(120),
                "reqId": token_hex(16),
                "src": Cloud.SRC,
                "stamp": self._timestamp(),
            },
        }

        # Login and store the session
        response = await self._api_request("/mj/user/login", body)

        # Assert response is not None since we should throw on errors
        assert response is not None

        self._session = response
        self._access_token = response["mdata"]["accessToken"]
        _LOGGER.debug("Received accessToken: %s", self._access_token)

    async def get_token(self, udpid):
        """Get token and key for the provided udpid."""

        response = await self._api_request(
            '/v1/iot/secure/getToken',
            self._build_request_body({"udpid": udpid})
        )

        # Assert response is not None since we should throw on errors
        assert response is not None

        for token in response["tokenlist"]:
            if token["udpId"] == udpid:
                return token["token"], token["key"]

        # No matching udpId in the tokenlist
        return None, None
