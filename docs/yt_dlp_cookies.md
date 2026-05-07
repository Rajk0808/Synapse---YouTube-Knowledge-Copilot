# yt-dlp YouTube Cookies Setup

This project uses `yt-dlp` as a fallback for extracting YouTube subtitles when the YouTube transcript API is blocked or unavailable.

## Why cookies are needed

Some YouTube videos require sign-in or bot verification. In those cases, `yt-dlp` needs a valid browser cookies file to access the video page and fetch subtitles.

## Environment variable

Set one of the following environment variables to point to your exported YouTube cookie file:

- `YT_DLP_COOKIES`
- `YTDLP_COOKIES_PATH`
- `YOUTUBE_COOKIES_PATH`

The code will automatically use the first one found.

## Export cookies from Chrome or Firefox

Use a browser extension like `Get cookies.txt` or `cookies.txt` to export cookies for `youtube.com`.

1. Install the extension.
2. Open `https://www.youtube.com` and sign in.
3. Export cookies to a file, for example `youtube_cookies.txt`.
4. Store the file somewhere secure.

## Example usage

### Windows PowerShell

```powershell
$env:YT_DLP_COOKIES = "C:\path\to\youtube_cookies.txt"
```

### Unix / macOS

```bash
export YT_DLP_COOKIES="/path/to/youtube_cookies.txt"
```

## Recommended deployment setup

Add the environment variable to your service configuration or `.env` file used by production deployment.

Example in a `.env` file:

```env
YT_DLP_COOKIES=/app/config/youtube_cookies.txt
```

Then load the `.env` file in your deployment environment before starting the app.

## Notes

- Keep the cookies file private.
- Renew the cookies file if YouTube signs you out or the session expires.
- If the video is still unavailable, the fallback may still fail if the video is genuinely private or has no subtitles.
