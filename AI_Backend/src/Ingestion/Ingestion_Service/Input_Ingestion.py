from datetime import datetime
from urllib.parse import urlparse, parse_qs
import os
import tempfile
import logging
logger = logging.getLogger(__name__)
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)


class _ObjectChain:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __or__(self, next_step):
        return _ObjectChain(self, next_step)

    def invoke(self, value):
        intermediate = self.left.invoke(value)
        return self.right.invoke(intermediate)


class Utils:
    def __or__(self, other):
        return _ObjectChain(self, other)

    # ── YouTube Data API client ───────────────────────────────────────────────

    def _get_youtube_client(self):
        """Build and return an authenticated YouTube Data API v3 client."""
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError(
                "YOUTUBE_API_KEY environment variable is not set. "
                "Get a key from Google Cloud Console → APIs → YouTube Data API v3."
            )
        return build("youtube", "v3", developerKey=api_key)

    # ── URL helpers ───────────────────────────────────────────────────────────

    def _extract_video_id(self, url: str) -> str:
        """Extracts a YouTube video ID from common URL formats."""
        logger.info('Extracting video ID. File : input_ingestion.py, Line : 401.')
        parsed = urlparse(url)

        if parsed.netloc in {"youtu.be", "www.youtu.be"}:
            return parsed.path.lstrip("/")

        if parsed.netloc in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
            if parsed.path == "/watch":
                return parse_qs(parsed.query).get("v", [""])[0]
            if parsed.path.startswith("/shorts/"):
                return parsed.path.split("/shorts/", 1)[1].split("/", 1)[0]
            if parsed.path.startswith("/embed/"):
                return parsed.path.split("/embed/", 1)[1].split("/", 1)[0]
        logger.info('Successfully extracted video ID. File : input_ingestion.py, Line : 409.')
        return ""

    def _extract_playlist_id(self, url: str) -> str:
        """Extracts a YouTube playlist ID from a URL."""
        logger.info('Extracting playlist ID. File : input_ingestion.py, Line : 414.')
        parsed = urlparse(url)
        return parse_qs(parsed.query).get("list", [""])[0]

    def _extract_channel_handle(self, url: str) -> str:
        """Extracts a channel handle or ID from a YouTube channel URL."""
        parsed = urlparse(url)
        path = parsed.path

        if path.startswith("/@"):
            return path.split("/@", 1)[1].split("/", 1)[0]
        if path.startswith("/channel/"):
            return path.split("/channel/", 1)[1].split("/", 1)[0]
        if path.startswith("/c/"):
            return path.split("/c/", 1)[1].split("/", 1)[0]
        if path.startswith("/user/"):
            return path.split("/user/", 1)[1].split("/", 1)[0]

        return path.lstrip("/").split("/", 1)[0]

    def _format_publish_date(self, upload_date: str | None) -> str | None:
        """Normalize various date formats to YYYY-MM-DD."""
        if not upload_date:
            return None

        # YouTube Data API returns ISO 8601 e.g. 2024-01-15T10:30:00Z
        if "T" in upload_date:
            try:
                return upload_date[:10]
            except Exception:
                return upload_date

        # yt-dlp returns YYYYMMDD
        try:
            return datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return upload_date

    # ── URL type detection ────────────────────────────────────────────────────

    def detect_youtube_url_type(self, url: str) -> str:
        """
        Detects the type of a YouTube URL.

        Returns:
            str: 'video', 'playlist', 'channel', 'video_in_playlist', or 'unknown'
        """
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        if ("si" in query and "list" in query) or ("list" in query and "v" in query):
            return "video_in_playlist"
        elif "list" in query:
            return "playlist"
        elif "si" in query or "v" in query:
            return "video"
        elif parsed.netloc in {"youtu.be", "www.youtu.be"}:
            return "video"
        elif parsed.path.startswith("/shorts/"):
            return "video"
        elif (
            parsed.path.startswith("/channel/")
            or parsed.path.startswith("/@")
            or parsed.path.startswith("/c/")
            or parsed.path.startswith("/user/")
        ):
            return "channel"
        else:
            return "unknown"

    # ── Metadata extraction via YouTube Data API ──────────────────────────────

    def _fetch_video_metadata(self, video_id: str) -> dict:
        """Fetch metadata for a single video using YouTube Data API."""
        youtube = self._get_youtube_client()

        response = (
            youtube.videos()
            .list(
                part="snippet,statistics,contentDetails",
                id=video_id,
            )
            .execute()
        )

        if not response.get("items"):
            raise ValueError(f"Video not found or unavailable: {video_id}")

        item = response["items"][0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content_details = item.get("contentDetails", {})

        return {
            "title": snippet.get("title"),
            "uploader": snippet.get("channelTitle"),
            "upload_date": snippet.get("publishedAt"),
            "duration": content_details.get("duration"),  # ISO 8601 e.g. PT4M13S
            "view_count": statistics.get("viewCount"),
            "like_count": statistics.get("likeCount"),
            "comment_count": statistics.get("commentCount"),
            "dislike_count": None,  # YouTube removed public dislike count
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
            "description": snippet.get("description"),
            "channel_id": snippet.get("channelId"),
        }

    def _fetch_playlist_metadata(self, playlist_id: str) -> dict:
        """Fetch metadata for a playlist using YouTube Data API."""
        youtube = self._get_youtube_client()

        response = (
            youtube.playlists()
            .list(
                part="snippet,contentDetails",
                id=playlist_id,
            )
            .execute()
        )

        if not response.get("items"):
            raise ValueError(f"Playlist not found or unavailable: {playlist_id}")

        item = response["items"][0]
        snippet = item.get("snippet", {})
        content_details = item.get("contentDetails", {})

        return {
            "title": snippet.get("title"),
            "uploader": snippet.get("channelTitle"),
            "upload_date": snippet.get("publishedAt"),
            "video_count": content_details.get("itemCount"),
            "description": snippet.get("description"),
            "channel_id": snippet.get("channelId"),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
        }

    def _fetch_channel_metadata(self, url: str) -> dict:
        """Fetch metadata for a channel using YouTube Data API."""
        youtube = self._get_youtube_client()
        handle = self._extract_channel_handle(url)

        # Try by handle first (@username), then by channel ID (UCxxx)
        if handle.startswith("UC"):
            response = (
                youtube.channels()
                .list(part="snippet,statistics", id=handle)
                .execute()
            )
        else:
            response = (
                youtube.channels()
                .list(part="snippet,statistics", forHandle=handle)
                .execute()
            )

        if not response.get("items"):
            raise ValueError(f"Channel not found: {handle}")

        item = response["items"][0]
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})

        return {
            "title": snippet.get("title"),
            "uploader": snippet.get("title"),
            "upload_date": snippet.get("publishedAt"),
            "subscriber_count": statistics.get("subscriberCount"),
            "view_count": statistics.get("viewCount"),
            "video_count": statistics.get("videoCount"),
            "description": snippet.get("description"),
            "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url"),
        }

    def extract_metadata(self, url: str, type: str) -> dict:
        """
        Extracts metadata from a YouTube URL based on its type.

        Args:
            url (str): The YouTube URL to extract metadata from.
            type (str): URL type — 'video', 'playlist', 'channel', or 'video_in_playlist'.

        Returns:
            dict: Extracted metadata.
        """
        if type == "video":
            video_id = self._extract_video_id(url)
            if not video_id:
                raise ValueError("Could not extract video ID from URL.")
            return self._fetch_video_metadata(video_id)

        elif type == "playlist":
            playlist_id = self._extract_playlist_id(url)
            if not playlist_id:
                raise ValueError("Could not extract playlist ID from URL.")
            return self._fetch_playlist_metadata(playlist_id)

        elif type == "channel":
            return self._fetch_channel_metadata(url)

        elif type == "video_in_playlist":
            video_id = self._extract_video_id(url)
            playlist_id = self._extract_playlist_id(url)

            if not video_id:
                raise ValueError("Could not extract video ID from URL.")

            video_meta = self._fetch_video_metadata(video_id)

            playlist_meta = {}
            if playlist_id:
                try:
                    playlist_meta = self._fetch_playlist_metadata(playlist_id)
                except ValueError:
                    pass  # playlist fetch is best-effort

            return {
                "video_title": video_meta.get("title"),
                "video_uploader": video_meta.get("uploader"),
                "video_upload_date": video_meta.get("upload_date"),
                "video_duration": video_meta.get("duration"),
                "video_view_count": video_meta.get("view_count"),
                "video_like_count": video_meta.get("like_count"),
                "video_dislike_count": video_meta.get("dislike_count"),
                "video_comment_count": video_meta.get("comment_count"),
                "video_thumbnail": video_meta.get("thumbnail"),
                "playlist_title": playlist_meta.get("title"),
                "playlist_uploader": playlist_meta.get("uploader"),
                "playlist_upload_date": playlist_meta.get("upload_date"),
                "playlist_video_count": playlist_meta.get("video_count"),
            }

        else:
            return {}

    # ── Supadata fallback ─────────────────────────────────────────────────────

    def _fetch_via_supadata(self, video_id: str, language: str = "en") -> list[dict]:
        """
        Fetch transcript via Supadata API.
        Requires SUPADATA_API_KEY environment variable.

        Supadata acts as a middleman — it fetches from YouTube using
        its own residential IPs, bypassing IP block issues on cloud hosts.

        Sign up free at https://supadata.ai to get your API key.
        Free tier: 100 requests/day.
        """
        import requests

        api_key = os.getenv("SUPADATA_API_KEY")
        if not api_key:
            raise ValueError("SUPADATA_API_KEY environment variable is not set.")

        logger.info(f"Fetching transcript via Supadata for video: {video_id}")

        response = requests.get(
            "https://api.supadata.ai/v1/youtube/transcript",
            params={"videoId": video_id, "lang": language},
            headers={"x-api-key": api_key},
            timeout=30,
        )

        if response.status_code == 429:
            raise ValueError("Supadata free tier daily limit (100 req/day) reached. Try again tomorrow.")
        if response.status_code == 404:
            raise ValueError(f"Supadata could not find transcript for video: {video_id}")
        if not response.ok:
            raise ValueError(f"Supadata API error {response.status_code}: {response.text}")

        data = response.json()

        # Supadata returns: { "content": [{"text": "...", "offset": 1234, "duration": 5000, "lang": "en"}, ...] }
        # offset and duration are in milliseconds
        segments = []
        for item in data.get("content", []):
            start_sec = item.get("offset", 0) / 1000.0
            duration_sec = item.get("duration", 0) / 1000.0
            text = item.get("text", "").strip()
            if not text:
                continue
            segments.append({
                "text": text,
                "start": start_sec,
                "duration": duration_sec,
            })

        if not segments:
            raise ValueError("Supadata returned an empty transcript.")

        logger.info(f"Supadata returned {len(segments)} transcript segments.")
        return segments

    # ── Transcript helpers ────────────────────────────────────────────────────

    def _fetch_transcript_items(self, video_id: str, language_priority: list[str]) -> list[dict]:
        logger.info('Fetching transcript items. File : input_ingestion.py, Line : 411.')
        api = YouTubeTranscriptApi()
        logger.info('api init done. File : input_ingestion.py, Line : 412.')
        transcript_obj = api.fetch(video_id, languages=language_priority)
        logger.info('transcript fetched done. File : input_ingestion.py, Line : 413.')
        if hasattr(transcript_obj, "to_raw_data"):
            logger.info('to_raw_data done. File : input_ingestion.py, Line : 415.')
            return transcript_obj.to_raw_data()
        logger.info('to_raw_data done. File : input_ingestion.py, Line : 415.')
        return [
            {
                "text": getattr(item, "text", ""),
                "start": getattr(item, "start", 0.0),
                "duration": getattr(item, "duration", 0.0),
            }
            for item in transcript_obj
        ]

    def _format_seconds(self, total_seconds: float) -> str:
        """Convert seconds to HH:MM:SS.mmm format."""
        milliseconds = int(round(total_seconds * 1000))
        seconds_part = (milliseconds // 1000) % 60
        minutes_part = (milliseconds // 60000) % 60
        hours_part = milliseconds // 3600000
        millis_part = milliseconds % 1000
        return f"{hours_part:02}:{minutes_part:02}:{seconds_part:02}.{millis_part:03}"

    def _get_yt_dlp_cookiefile(self) -> str | None:
        """
        Return a yt-dlp cookiefile path.

        Supports two modes:
        1. YOUTUBE_COOKIES_CONTENT — paste the full cookies.txt content as an env var.
           The method writes it to a temp file and returns the path.
           Use this on cloud hosts like Render where you can't upload files.

        2. File path env vars — YT_DLP_COOKIES / YTDLP_COOKIES_PATH / YOUTUBE_COOKIES_PATH
           Point these to an actual cookies.txt file on disk.

        How to export cookies:
        - Install "Get cookies.txt LOCALLY" extension in Chrome/Firefox
        - Visit youtube.com while logged in
        - Export cookies → copy the file content
        - Paste into YOUTUBE_COOKIES_CONTENT env var on Render
        Note: Cookies expire every ~2-4 weeks and will need to be refreshed.
        """
        # Mode 1: cookie content pasted directly as env var (best for Render)
        cookie_content = os.getenv("YOUTUBE_COOKIES_CONTENT")
        if cookie_content:
            try:
                tmp = tempfile.NamedTemporaryFile(
                    mode="w", suffix=".txt", delete=False, prefix="yt_cookies_"
                )
                tmp.write(cookie_content)
                tmp.flush()
                tmp.close()
                logger.info(f"Wrote YouTube cookies to temp file: {tmp.name}")
                return tmp.name
            except Exception as e:
                logger.warning(f"Failed to write cookie content to temp file: {e}")

        # Mode 2: path to cookies file on disk
        for env_name in ["YT_DLP_COOKIES", "YTDLP_COOKIES_PATH", "YOUTUBE_COOKIES_PATH"]:
            cookiefile = os.getenv(env_name)
            if cookiefile:
                return cookiefile

        return None

    def _parse_vtt_subtitles(self, vtt_text: str) -> list[dict]:
        """Parse VTT subtitle content into transcript segments."""
        import re

        cue_pattern = re.compile(
            r"(?P<start>\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2}\.\d{3})"
        )

        def ts_to_sec(ts: str) -> float:
            h, m, s = ts.split(":")
            sec, ms = s.split(".")
            return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000

        segments = []
        lines = vtt_text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            m = cue_pattern.match(line)
            if m:
                start_sec = ts_to_sec(m.group("start"))
                end_sec = ts_to_sec(m.group("end"))
                i += 1
                text_parts = []
                while i < len(lines) and lines[i].strip():
                    text_parts.append(lines[i].strip())
                    i += 1
                text = " ".join(text_parts)
                if text:
                    segments.append(
                        {
                            "text": text,
                            "start": start_sec,
                            "duration": end_sec - start_sec,
                            "end": end_sec,
                            "timecode": f"{self._format_seconds(start_sec)} --> {self._format_seconds(end_sec)}",
                        }
                    )
            i += 1
        return segments

    def _fetch_subtitles_with_yt_dlp(self, video_id: str, language_priority: list[str]) -> list[dict]:
        """Use yt-dlp to fetch subtitles and return them as transcript segments."""
        try:
            from yt_dlp import YoutubeDL
        except Exception as exc:
            raise ValueError("yt-dlp is required for transcript fallback but is not installed.") from exc

        ydl_opts = {
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": language_priority,
            "subtitlesformat": "vtt",
            "quiet": True,
            "no_warnings": True,
        }

        cookiefile = self._get_yt_dlp_cookiefile()
        if cookiefile:
            ydl_opts["cookiefile"] = cookiefile
            logger.info("Using cookies file for yt-dlp.")
        else:
            logger.warning(
                "No cookies file found for yt-dlp. "
                "Set YOUTUBE_COOKIES_CONTENT on Render for better success rate."
            )

        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)

        subtitle_sources = (
            info.get("subtitles", {})
            or info.get("requested_subtitles", {})
            or info.get("automatic_captions", {})
        )

        if not subtitle_sources:
            raise ValueError(
                "yt-dlp was unable to find subtitles for this video. "
                "If the video requires sign-in, set a valid cookies file via YOUTUBE_COOKIES_CONTENT."
            )

        import requests

        for lang in language_priority:
            if lang in subtitle_sources:
                sub_entry = subtitle_sources[lang][0]
                if not sub_entry.get("url"):
                    continue
                resp = requests.get(sub_entry["url"], timeout=10)
                resp.raise_for_status()
                vtt_text = resp.text
                segments = self._parse_vtt_subtitles(vtt_text)
                if segments:
                    return segments

        raise ValueError(
            "yt-dlp subtitle fallback failed: no usable subtitles were found for the requested languages. "
            "Try a different language or supply a YouTube cookies file via YOUTUBE_COOKIES_CONTENT."
        )

    def _fetch_with_fallback_chain(self, video_id: str, language_priority: list[str]) -> list[dict]:
        """
        Central fallback chain for transcript fetching.

        Priority order:
          1. YouTubeTranscriptApi (direct, fastest)
          2. Supadata API         (bypasses IP blocks on cloud hosts — free 100 req/day)
          3. yt-dlp               (last resort, needs cookies on cloud hosts)

        On cloud hosts like Render, step 1 will usually fail with IpBlocked.
        Step 2 (Supadata) will handle the majority of cases for free.
        Step 3 is the final safety net if Supadata quota is exhausted.
        """
        errors = []

        # ── Step 1: Direct YouTubeTranscriptApi ──────────────────────────────
        try:
            logger.info(f"[Transcript] Trying YouTubeTranscriptApi for video: {video_id}")
            return self._fetch_transcript_items(video_id, language_priority)
        except (IpBlocked, RequestBlocked) as exc:
            logger.warning(f"[Transcript] YouTubeTranscriptApi IP blocked: {exc}")
            errors.append(f"YouTubeTranscriptApi (IP blocked): {exc}")
        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            logger.warning(f"[Transcript] No transcript found via YouTubeTranscriptApi: {exc}")
            errors.append(f"YouTubeTranscriptApi (no transcript): {exc}")
        except VideoUnavailable as exc:
            # No point trying further — video itself is unavailable
            raise ValueError("Video is unavailable or private.") from exc

        # ── Step 2: Supadata API ─────────────────────────────────────────────
        supadata_key = os.getenv("SUPADATA_API_KEY")
        if supadata_key:
            try:
                logger.info(f"[Transcript] Trying Supadata for video: {video_id}")
                return self._fetch_via_supadata(video_id, language_priority[0])
            except ValueError as exc:
                logger.warning(f"[Transcript] Supadata failed: {exc}")
                errors.append(f"Supadata: {exc}")
        else:
            logger.info("[Transcript] Supadata skipped — SUPADATA_API_KEY not set.")
            errors.append("Supadata: SUPADATA_API_KEY not configured.")

        # ── Step 3: yt-dlp with cookies ──────────────────────────────────────
        try:
            logger.info(f"[Transcript] Trying yt-dlp fallback for video: {video_id}")
            return self._fetch_subtitles_with_yt_dlp(video_id, language_priority)
        except Exception as exc:
            logger.warning(f"[Transcript] yt-dlp fallback failed: {exc}")
            errors.append(f"yt-dlp: {exc}")

        # ── All methods failed ───────────────────────────────────────────────
        cookie_hint = (
            "To improve success rate on cloud hosts:\n"
            "  • Set SUPADATA_API_KEY (free at https://supadata.ai)\n"
            "  • Or set YOUTUBE_COOKIES_CONTENT with your browser cookies\n"
            "    (export via 'Get cookies.txt LOCALLY' Chrome/Firefox extension)"
        )
        raise ValueError(
            f"All transcript fetching methods failed for video '{video_id}'.\n"
            f"{cookie_hint}\n\n"
            f"Individual errors:\n" + "\n".join(f"  - {e}" for e in errors)
        )

    def extract_transcript(self, url: str, languages: list[str] | None = None) -> list[dict]:
        """
        Extract plain transcript text (no timestamps).

        Returns:
            list[dict]: Full transcript as a list of dictionaries with
                        'text', 'start', and 'duration' fields.
        """
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL. Could not extract video ID.")

        language_priority = languages or ["en"]
        return self._fetch_with_fallback_chain(video_id, language_priority)

    def extract_time_aware_transcript(
        self, url: str, languages: list[str] | None = None
    ) -> list[dict]:
        """
        Extract transcript segments with timing information.

        Returns:
            list[dict]: Segments with text/start/end/duration/timecode fields.
        """
        logger.info('Extracting time aware transcript. File : input_ingestion.py, Line : 400.')
        video_id = self._extract_video_id(url)
        if not video_id:
            logger.error('Invalid YouTube URL. Could not extract video ID. File : input_ingestion.py, Line : 405.')
            raise ValueError("Invalid YouTube URL. Could not extract video ID.")

        language_priority = languages or ["en"]

        # Use the unified fallback chain
        transcript_items = self._fetch_with_fallback_chain(video_id, language_priority)

        segments = []
        for item in transcript_items:
            start = float(item.get("start", 0.0))
            duration = float(item.get("duration", 0.0))
            end = start + duration
            text = item.get("text", "").strip()

            if not text:
                continue

            segments.append(
                {
                    "text": text,
                    "start": start,
                    "duration": duration,
                    "end": end,
                    "timecode": f"{self._format_seconds(start)} --> {self._format_seconds(end)}",
                }
            )

        logger.info(f'Extraction done — {len(segments)} segments. File : input_ingestion.py')
        return segments

    # ── Main entry point ──────────────────────────────────────────────────────

    def invoke(self, data: dict) -> dict:
        """
        Main method to process a YouTube URL and extract metadata and transcript.

        Args:
            data (dict): Must contain 'url'. Optional: 'languages', 'notebook_id',
                         'user_id', 'source_id'.

        Returns:
            dict: Combined metadata and transcript (if available).
        """
        url = data.get("url")

        if not url:
            logger.info('Url not found, File input ingestion : line 461')
            raise ValueError("'url' is required in input data.")

        languages = data.get("languages")
        workspace_id = data.get("notebook_id")
        logger.info('Starting detect url type, file input_ingestion, line : 466')
        url_type = self.detect_youtube_url_type(url)
        logger.info('Extracting MetaData, file input_ingestion, line : 468')
        metadata = self.extract_metadata(url, url_type)

        metadata["type"] = url_type
        metadata["source_url"] = url
        logger.info('Formating publishing date, file input_ingestion, line : 473')
        metadata["published_at"] = self._format_publish_date(
            metadata.get("upload_date") or metadata.get("video_upload_date")
        )
        metadata["notebook_id"] = workspace_id
        metadata["user_id"] = data.get("user_id")
        metadata["source_id"] = data.get("source_id")

        if url_type in {"video", "video_in_playlist"}:
            try:
                logger.info('Extracting transcript, file input_ingestion, line : 483')
                transcript = self.extract_transcript(url, languages)
                metadata["transcript"] = transcript
            except ValueError as exc:
                logger.error(
                    f'Error during extraction of transcript. '
                    f'file : input_ingestion.py, Line : 487, error : {exc}'
                )
                metadata["transcript_error"] = str(exc)

        return metadata