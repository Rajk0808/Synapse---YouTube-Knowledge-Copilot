from datetime import datetime
from urllib.parse import urlparse, parse_qs
import os
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

    def extract_transcript(self, url: str, languages: list[str] | None = None) -> str:
        """
        Extract plain transcript text (no timestamps).

        Returns:
            str: Full transcript as a single string.
        """
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL. Could not extract video ID.")

        language_priority = languages or ["en"]

        try:
            transcript_items = self._fetch_transcript_items(video_id, language_priority)
            return " ".join(
                item.get("text", "") for item in transcript_items if item.get("text")
            )
        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            # Try to fetch subtitles using yt-dlp as a fallback when YouTube captions are unavailable
            try:
                from yt_dlp import YoutubeDL
                ydl_opts = {
                    "skip_download": True,
                    "writesubtitles": True,
                    "subtitleslangs": language_priority,
                    "quiet": True,
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
                    subs = info.get("subtitles", {})
                    # Prefer the first requested language that exists
                    for lang in language_priority:
                        if lang in subs:
                            # subtitles are provided as a list of dicts with 'url'
                            sub_url = subs[lang][0]["url"]
                            # Fetch the subtitle file
                            import requests
                            sub_resp = requests.get(sub_url, timeout=10)
                            sub_resp.raise_for_status()
                            # Simple extraction of text from VTT/TTML (strip timestamps and markup)
                            import re
                            text = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}", "", sub_resp.text)
                            text = re.sub(r"<[^>]+>", "", text)  # remove any HTML/TTML tags
                            text = re.sub(r"\s+", " ", text).strip()
                            if text:
                                return text
            except Exception as yt_exc:
                # Log the secondary failure and re‑raise the original exception for consistent API response
                logger.warning(f"yt-dlp subtitle fallback failed for video {video_id}: {yt_exc}")
                raise ValueError(
                        "Transcript is not available for this video and yt-dlp fallback also failed. "
                        "The video might have captions disabled, no captions in the requested languages, "
                        "be too short, or require YouTube login to access. "
                        f"Original error: {exc}" ) from exc
        except (IpBlocked, RequestBlocked) as exc:
            raise ValueError(
                "YouTube is blocking transcript requests from this IP/network right now. "
                "Try again later or run from a different network."
            ) from exc
        except VideoUnavailable as exc:
            raise ValueError("Video is unavailable or private.") from exc

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

        try:
            logger.info('Fetching transcript items. File : input_ingestion.py, Line : 411.')
            transcript_items = self._fetch_transcript_items(video_id, language_priority)
            segments = []

            for item in transcript_items:
                start = float(item.get("start", 0.0))
                duration = float(item.get("duration", 0.0))
                end = start + duration
                text = item.get("text", "")

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
            logger.info('Extraction done, File : input_ingestion.py, line : 436')
            return segments

        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            logger.error('Transcript not found or disabled. File : input_ingestion.py, line : 440')
            raise ValueError(
                "Transcript is not available for this video. "
                f"The video likely has captions disabled, no captions in {language_priority}, "
                "or requires YouTube login to access."
            ) from exc
        except (IpBlocked, RequestBlocked) as exc:
            logger.error('Transcript request block , File : input_ingestion.py, line : 447')
            raise ValueError(
                "YouTube is blocking transcript requests from this IP/network right now. "
                "Try again later or run from a different network."
            ) from exc
        except VideoUnavailable as exc:
            logger.error('Video is unavailable or private., File : input_ingestion.py, line : 453')
            raise ValueError("Video is unavailable or private.") from exc

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
                logger.info('Extrating Time aware transcript, file input_ingestion, line : 483')
                transcript = self.extract_time_aware_transcript(url, languages)
                metadata["transcript"] = transcript
            except ValueError as exc:
                logger.error('Error during extraction of time aware transcript. file : input_ingestion.py, Line : 487')
                metadata["transcript_error"] = str(exc)

        return metadata

