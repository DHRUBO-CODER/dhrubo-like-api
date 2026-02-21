import os
import random
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
import httpx
import asyncio
from typing import Dict, Any, Optional, Tuple

# ==================== কনফিগারেশন ====================

API_URL = "https://info-api-mg24-pro.vercel.app/get?uid={}"
CREDIT = "—͞Dʜʀᴜʙᴏ"
LIKE_VALUES = [111, 134, 183, 199, 121, 200]
TG = "@DHRUBO_X_TCP"

HIDDEN_API_URL = API_URL
HIDDEN_CREDIT = CREDIT
HIDDEN_LIKE_VALUES = LIKE_VALUES
HIDDEN_TELEGRAM_ID = TG


# ==================== ডাটা মডেল ====================

class PlayerData:
    def __init__(self, uid: str, server: str, nickname: str, likes_before: int, likes_given: int):
        self.uid = uid
        self.server = server
        self.nickname = nickname
        self.after_likes = likes_before
        self.before_likes = max(0, likes_before - likes_given)
        self.likes_given = likes_given

    def to_dict(self) -> Dict[str, Any]:
        return {
            "LikesGivenByAPI": self.likes_given,
            "LikesbeforeCommand": self.before_likes,
            "LikesafterCommand": self.after_likes,
            "PlayerNickname": self.nickname,
            "UID": self.uid,
            "server": self.server,
            "source": HIDDEN_CREDIT,
            "telegram_id": HIDDEN_TELEGRAM_ID,
            "devolved_by": HIDDEN_CREDIT
        }


class ErrorResponse:
    @staticmethod
    def create(message: str, status_code: int = 400) -> Dict[str, Any]:
        return {
            "status": 0,
            "error": message,
            "source": HIDDEN_CREDIT,
            "code": status_code
        }


# ==================== API ফাংশন ====================

class LikeAPI:

    def __init__(self):
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0

        # 🔒 Daily limit config
        self.limit_file = "daily_limits.json"
        self.daily_limit_seconds = 86400

        if not os.path.exists(self.limit_file):
            with open(self.limit_file, "w") as f:
                json.dump({}, f)

    def load_limits(self):
        with open(self.limit_file, "r") as f:
            return json.load(f)

    def save_limits(self, data):
        with open(self.limit_file, "w") as f:
            json.dump(data, f)

    async def fetch_player_data(self, uid: str) -> Optional[Dict[str, Any]]:
        try:
            target_url = HIDDEN_API_URL.format(uid)
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(target_url)
                response.raise_for_status()
                return response.json()

        except httpx.TimeoutException:
            return {"error": "timeout"}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"error": "not_found"}
            return {"error": "http_error"}
        except Exception:
            return {"error": "unknown"}

    def extract_player_info(self, data: Dict[str, Any]) -> Tuple[str, int]:
        account_info = data.get("AccountInfo", {})
        nickname = account_info.get("AccountName", "Unknown Player")
        likes = account_info.get("AccountLikes", 0)
        return nickname, likes

    def generate_likes(self) -> int:
        return random.choice(HIDDEN_LIKE_VALUES)

    def validate_uid(self, uid: str) -> bool:
        return uid and uid.isdigit() and len(uid) <= 20

    async def process_request(self, uid: str, server: str) -> Dict[str, Any]:
        self.request_count += 1

        if not self.validate_uid(uid):
            self.error_count += 1
            return ErrorResponse.create("Invalid UID format", 400)

        # 🔒 Daily limit check
        limits = self.load_limits()
        current_time = int(time.time())

        if uid in limits:
            last_time = limits[uid]
            if current_time - last_time < self.daily_limit_seconds:
                self.error_count += 1
                remaining = self.daily_limit_seconds - (current_time - last_time)
                hours_left = remaining // 3600
                return ErrorResponse.create(
                    f"This UID already received likes today. Try again after {hours_left} hours.",
                    429
                )

        player_data = await self.fetch_player_data(uid)

        if not player_data:
            self.error_count += 1
            return ErrorResponse.create("Player not found", 404)

        if isinstance(player_data, dict) and "error" in player_data:
            self.error_count += 1
            return ErrorResponse.create("Service error", 503)

        nickname, likes_before = self.extract_player_info(player_data)
        likes_given = self.generate_likes()

        player = PlayerData(uid, server, nickname, likes_before, likes_given)

        # 🔒 Save success time
        limits[uid] = current_time
        self.save_limits(limits)

        self.success_count += 1
        return player.to_dict()

    def get_stats(self) -> Dict[str, Any]:
        total = max(self.request_count, 1)
        return {
            "total_requests": self.request_count,
            "successful": self.success_count,
            "failed": self.error_count,
            "success_rate": f"{(self.success_count / total) * 100:.1f}%",
            "source": HIDDEN_CREDIT
        }


like_api = LikeAPI()


# ==================== SERVER HANDLER ====================

class handler(BaseHTTPRequestHandler):

    def do_GET(self):

        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        if path == "/" or path == "":
            response = {
                "message": "Like API is running",
                "endpoints": {
                    "/like": "GET with ?uid={uid}&server={server}",
                    "/stats": "GET API statistics"
                },
                "source": HIDDEN_CREDIT,
                "status": "active"
            }
            self.wfile.write(json.dumps(response, indent=2).encode())
            return

        if path == "/stats":
            self.wfile.write(json.dumps(like_api.get_stats(), indent=2).encode())
            return

        if path == "/like":
            uid = query_params.get('uid', [''])[0]
            server = query_params.get('server', [''])[0]

            if not uid or not server:
                self.wfile.write(json.dumps(
                    ErrorResponse.create("Missing uid or server parameter", 400)
                ).encode())
                return

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(like_api.process_request(uid, server))
            loop.close()

            self.wfile.write(json.dumps(result, indent=2).encode())
            return

        self.wfile.write(json.dumps(
            ErrorResponse.create("Endpoint not found", 404)
        ).encode())

    def log_message(self, format, *args):
        return


# ==================== RUN LOCAL ====================

def run_local_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, handler)
    print(f"🚀 Server running at http://localhost:{port}/")
    httpd.serve_forever()


if __name__ == "__main__":
    run_local_server(8000)