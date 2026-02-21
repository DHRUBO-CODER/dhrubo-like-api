import random
import json
import asyncio
import httpx
from typing import Dict, Any, Optional, Tuple
from urllib.parse import parse_qs

# ==================== CONFIG ====================

API_URL = "https://info-api-mg24-pro.vercel.app/get?uid={}"
CREDIT = "—͞Dʜʀᴜʙᴏ"
LIKE_VALUES = [111, 134, 183, 199, 121, 200]
TG = "@DHRUBO_X_TCP"

HIDDEN_API_URL = API_URL
HIDDEN_CREDIT = CREDIT
HIDDEN_LIKE_VALUES = LIKE_VALUES
HIDDEN_TELEGRAM_ID = TG

# ==================== DAILY LIMIT STORAGE ====================
# Vercel serverless এ ফাইল persistent নয়, তাই simple memory use
# এক UID একদিনে একবার
uid_daily_record: Dict[str, str] = {}  # uid -> date string "YYYY-MM-DD"

# ==================== PLAYER DATA ====================

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

# ==================== API ====================

class LikeAPI:
    def __init__(self):
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0

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
        return uid.isdigit() and len(uid) <= 20

    async def process_request(self, uid: str, server: str) -> Dict[str, Any]:
        import datetime

        self.request_count += 1

        # UID validation
        if not self.validate_uid(uid):
            self.error_count += 1
            return ErrorResponse.create("Invalid UID format", 400)

        # Check daily limit
        today = datetime.date.today().isoformat()
        last_request = uid_daily_record.get(uid)
        if last_request == today:
            return ErrorResponse.create("UID already used today", 429)
        uid_daily_record[uid] = today

        # Fetch player data
        player_data = await self.fetch_player_data(uid)
        if not player_data:
            self.error_count += 1
            return ErrorResponse.create("Player not found", 404)

        if "error" in player_data:
            self.error_count += 1
            error_map = {
                "timeout": "Service timeout",
                "not_found": "Player not found",
                "http_error": "Service unavailable",
                "unknown": "Unknown error"
            }
            status_code = 503 if player_data["error"] == "timeout" else 404
            return ErrorResponse.create(error_map.get(player_data["error"], "Unknown error"), status_code)

        nickname, likes_before = self.extract_player_info(player_data)
        likes_given = self.generate_likes()

        player = PlayerData(uid, server, nickname, likes_before, likes_given)
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

# ==================== VERCEL HANDLER ====================

async def handler(request):
    """Vercel serverless entrypoint"""
    path = request.path
    query = parse_qs(request.query_string.decode())

    if path == "/" or path == "":
        return {
            "message": "Like API is running",
            "source": HIDDEN_CREDIT,
            "status": "active"
        }

    if path == "/stats":
        return like_api.get_stats()

    if path == "/like":
        uid = query.get("uid", [""])[0]
        server = query.get("server", [""])[0]
        if not uid or not server:
            return ErrorResponse.create("Missing uid or server parameter", 400)
        return await like_api.process_request(uid, server)

    return ErrorResponse.create("Endpoint not found", 404)
