from datetime import datetime
from urllib.parse import urlparse, parse_qs
import os
from typing import Any, cast
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
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

    def _format_publish_date(self, upload_date: str | None) -> str | None:
        """Convert yt-dlp upload dates from YYYYMMDD to YYYY-MM-DD."""

        if not upload_date:
            return None

        try:
            return datetime.strptime(upload_date, "%Y%m%d").strftime("%Y-%m-%d")
        except ValueError:
            return upload_date

    def _build_ydl_options(self) -> dict[str, Any]:
        """Build yt-dlp options, optionally enabling authenticated cookie access."""

        ydl_opts: dict[str, Any] = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
        }

        cookie_file = os.getenv("YTDLP_COOKIES_FILE", "").strip()
        browser_cookie_source = os.getenv("YTDLP_COOKIES_FROM_BROWSER", "").strip()

        if cookie_file:
            ydl_opts["cookiefile"] = cookie_file

        if browser_cookie_source:
            # Format example: chrome OR firefox:default-release
            ydl_opts["cookiesfrombrowser"] = tuple(part for part in browser_cookie_source.split(":") if part)

        return ydl_opts

    def _safe_extract_info(self, ydl: YoutubeDL, url: str) -> dict[str, Any]:
        """Extract metadata and convert yt-dlp errors into actionable ValueErrors."""

        try:
            info = ydl.extract_info(url, download=False)
            return dict(info)
        except DownloadError as exc:
            message = str(exc)

            if "Sign in to confirm you're not a bot" in message:
                raise ValueError(
                    "YouTube requires authenticated cookies for this request. "
                    "Set YTDLP_COOKIES_FROM_BROWSER (example: chrome) or YTDLP_COOKIES_FILE "
                    "to a cookies.txt export, then retry."
                ) from exc

            raise ValueError(f"Failed to extract YouTube metadata: {message}") from exc

    def _extract_video_id(self, url: str) -> str:
        """Extracts a YouTube video ID from common URL formats."""

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

        return ""

    def detect_youtube_url_type(self, url : str) -> str:
        """
        Detects the type of a YouTube URL (video, playlist, channel, or unknown).

        Args:
            url (str): The YouTube URL to analyze.

        Returns:
            str: The type of the YouTube URL ('video', 'playlist', 'channel', or 'unknown').
        """
        
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        if ('si' in query and 'list' in query) or ('list' in query and 'v' in query):
            return 'video_in_playlist'
        elif 'list' in query:
            return 'playlist'
        elif 'si' in query or 'v' in query:
            return 'video'
        elif parsed.path.startswith('/channel/'):
            return 'channel'
        else:
            return 'unknown'
    
    def extract_metadata(self, url: str, type: str) -> dict:
        """
        Extracts metadata from a YouTube URL based on its type.

        Args:
            url (str): The YouTube URL to extract metadata from.
            type (str): The type of the YouTube URL ('video', 'playlist', 'channel', or 'video_in_playlist').

        Returns:
            dict: A dictionary containing the extracted metadata.
        """
        
        ydl_opts = self._build_ydl_options()

        with YoutubeDL(cast(Any, ydl_opts)) as ydl:
            if type == 'video':
                info = self._safe_extract_info(ydl, url)
                return {
                    'title': info.get('title'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'duration': info.get('duration'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                    'dislike_count': info.get('dislike_count'),
                    'comment_count': info.get('comment_count')
                }
            elif type == 'playlist':
                info = self._safe_extract_info(ydl, url)
                return {
                    'title': info.get('title'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'video_count': len(info.get('entries', []))
                }
            elif type == 'channel':
                info = self._safe_extract_info(ydl, url)
                return {
                    'title': info.get('title'),
                    'uploader': info.get('uploader'),
                    'upload_date': info.get('upload_date'),
                    'subscriber_count': info.get('subscriber_count')
                }
            elif type == 'video_in_playlist':
                video_info = self._safe_extract_info(ydl, url)
                parsed = urlparse(url)
                query = parse_qs(parsed.query)
                playlist_id = query.get('list', [None])[0]
                playlist_url = f'https://www.youtube.com/playlist?list={playlist_id}' if playlist_id else url
                playlist_info = self._safe_extract_info(ydl, playlist_url)
                return {
                    'video_title': video_info.get('title'),
                    'video_uploader': video_info.get('uploader'),
                    'video_upload_date': video_info.get('upload_date'),
                    'video_duration': video_info.get('duration'),
                    'video_view_count': video_info.get('view_count'),
                    'video_like_count': video_info.get('like_count'),
                    'video_dislike_count': video_info.get('dislike_count'),
                    'video_comment_count': video_info.get('comment_count'),
                    'playlist_title': playlist_info.get('title'),
                    'playlist_uploader': playlist_info.get('uploader'),
                    'playlist_upload_date': playlist_info.get('upload_date'),
                    'playlist_video_count': len(playlist_info.get('entries', []))
                }
            else:
                return {}

    def _fetch_transcript_items(self, video_id: str, language_priority: list[str]) -> list[dict]:
        """Fetch transcript items as raw dicts with text/start/duration keys."""

        # Backward compatibility with older youtube-transcript-api releases.
        get_transcript = getattr(YouTubeTranscriptApi, "get_transcript", None)
        if callable(get_transcript):
            return cast(list[dict], get_transcript(video_id, languages=language_priority))

        # Newer releases expose an instance method: fetch(...).
        api = YouTubeTranscriptApi()
        transcript_obj = api.fetch(video_id, languages=language_priority)

        if hasattr(transcript_obj, "to_raw_data"):
            return transcript_obj.to_raw_data()

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

    def extract_transcript(self, url : str, languages: list[str] | None = None) -> str:
        """
        Extract plain transcript text.

        Returns:
            str: Transcript text without timestamps.
        """

        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL. Could not extract video ID.")

        language_priority = languages or ["en"]

        try:
            transcript_items = self._fetch_transcript_items(video_id, language_priority)
            return " ".join(item.get("text", "") for item in transcript_items if item.get("text"))

        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            raise ValueError(
                "Transcript is not available for this video. "
                f"The video likely has captions disabled or no captions in {language_priority}."
            ) from exc
        except (IpBlocked, RequestBlocked) as exc:
            raise ValueError(
                "YouTube is blocking transcript requests from this IP/network right now. "
                "Try again later or run from a different network."
            ) from exc
        except VideoUnavailable as exc:
            raise ValueError("Video is unavailable or private.") from exc

    def extract_time_aware_transcript(self, url: str, languages: list[str] | None = None) -> list[dict]:
        """
        Extract transcript segments with timing information.

        Returns:
            list[dict]: A list of segments with text/start/end/duration/timecode fields.
        """

        video_id = self._extract_video_id(url)
        if not video_id:
            raise ValueError("Invalid YouTube URL. Could not extract video ID.")

        language_priority = languages or ["en"]

        try:
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

            return segments

        except (TranscriptsDisabled, NoTranscriptFound) as exc:
            raise ValueError(
                "Transcript is not available for this video. "
                f"The video likely has captions disabled or no captions in {language_priority}."
            ) from exc
        except (IpBlocked, RequestBlocked) as exc:
            raise ValueError(
                "YouTube is blocking transcript requests from this IP/network right now. "
                "Try again later or run from a different network."
            ) from exc
        except VideoUnavailable as exc:
            raise ValueError("Video is unavailable or private.") from exc
       
    def invoke(self, data) -> dict:
        """
        Main method to process a YouTube URL and extract metadata and transcript.

        Args:
            data (dict): A dictionary containing the YouTube URL and preferred transcript languages.
        """
        url = data.get("url")
        languages = data.get("languages")
        workspace_id = data.get("workspace_id")
        owner_user_id = data.get("owner_user_id")

        url_type = self.detect_youtube_url_type(url)
        metadata = self.extract_metadata(url, url_type)
        metadata["type"] = url_type
        metadata["source_url"] = url
        metadata["published_at"] = self._format_publish_date(metadata.get("upload_date"))
        metadata["workspace_id"] = workspace_id
        metadata["owner_user_id"] = owner_user_id

        if url_type in {'video', 'video_in_playlist'}:
            try:
                transcript = self.extract_time_aware_transcript(url, languages)
                metadata['transcript'] = transcript
            except ValueError as exc:
                metadata['transcript_error'] = str(exc)

        return metadata

