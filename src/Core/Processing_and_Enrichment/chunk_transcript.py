"""
Chunk Transcript Module

This module is responsible for dividing the cleaned transcript into smaller,
manageable chunks for further processing or analysis.
"""

from typing import Any


class ChunkTranscript:
    def __init__(self, chunk_size: int = 90, overlap: int = 15):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def invoke(self, segments: dict[str, Any]) -> dict[str, Any]:
        """
        Chunk cleaned transcript segments into smaller pieces.

        Handles:
        - Grouping transcript into 60-120 second time-aware chunks
        - Creating 10-20 second overlap between adjacent chunks
        - Preserving timing information for each chunk

        Input / Output:
            [{"text": str, "start": float, "end": float, "timecode": str}]
        """

        transcript = self._extract_transcript_segments(segments)
        segments["transcript_chunks"] = self.chunk_transcript(transcript, self.chunk_size, self.overlap)
        return segments

    def _extract_transcript_segments(
        self, payload: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Normalize transcript payloads into a list of transcript segment dicts."""

        transcript = payload.get("transcript", [])

        if isinstance(transcript, dict):
            transcript = transcript.get("transcript", [])

        if not isinstance(transcript, list):
            return []

        return [item for item in transcript if isinstance(item, dict)]

    def _format_seconds(self, total_seconds: float) -> str:
        """Convert seconds to HH:MM:SS.mmm format."""

        milliseconds = int(round(total_seconds * 1000))
        seconds_part = (milliseconds // 1000) % 60
        minutes_part = (milliseconds // 60000) % 60
        hours_part = milliseconds // 3600000
        millis_part = milliseconds % 1000
        return f"{hours_part:02}:{minutes_part:02}:{seconds_part:02}.{millis_part:03}"

    def chunk_transcript(
        self,
        segments: list[dict[str, Any]],
        chunk_size: int = 90,
        overlap: int = 15,
    ) -> list[dict[str, Any]]:
        """
        Group transcript segments into time-aware chunks.

        Rules:
        - Targets chunks around ``chunk_size`` seconds.
        - Keeps chunks between 60 and 120 seconds when possible.
        - Starts the next chunk about ``overlap`` seconds before the previous one ends.
        """

        if not segments:
            return []

        min_chunk_duration = 60.0
        max_chunk_duration = 120.0
        target_chunk_duration = min(max(float(chunk_size), min_chunk_duration), max_chunk_duration)
        overlap_duration = max(0.0, float(overlap))

        normalized_segments = sorted(
            [segment for segment in segments if isinstance(segment, dict)],
            key=lambda seg: (float(seg.get("start", 0.0)), float(seg.get("end", 0.0))),
        )

        if not normalized_segments:
            return []

        chunks: list[dict[str, Any]] = []
        start_idx = 0

        while start_idx < len(normalized_segments):
            chunk_segments: list[dict[str, Any]] = []
            chunk_start = float(normalized_segments[start_idx].get("start", 0.0))
            chunk_end = chunk_start
            end_idx = start_idx

            while end_idx < len(normalized_segments):
                segment = normalized_segments[end_idx]
                segment_end = float(segment.get("end", segment.get("start", 0.0)))
                candidate_duration = segment_end - chunk_start

                chunk_segments.append(segment)
                chunk_end = segment_end
                text = str(segment.get("text", "")).strip()
                reached_min = candidate_duration >= min_chunk_duration
                reached_target = candidate_duration >= target_chunk_duration
                would_exceed_max = False

                if end_idx + 1 < len(normalized_segments):
                    next_end = float(
                        normalized_segments[end_idx + 1].get(
                            "end",
                            normalized_segments[end_idx + 1].get("start", 0.0),
                        )
                    )
                    would_exceed_max = (next_end - chunk_start) > max_chunk_duration

                if reached_min and (
                    would_exceed_max
                    or (reached_target and text.endswith((".", "!", "?")))
                ):
                    break

                if candidate_duration >= max_chunk_duration:
                    break

                end_idx += 1

            chunk_text = " ".join(
                str(segment.get("text", "")).strip()
                for segment in chunk_segments
                if str(segment.get("text", "")).strip()
            )

            chunks.append(
                {
                    "chunk_id": len(chunks) + 1,
                    "text": chunk_text,
                    "start": chunk_start,
                    "end": chunk_end,
                    "duration": round(chunk_end - chunk_start, 3),
                    "timecode": (
                        f"{self._format_seconds(chunk_start)} --> "
                        f"{self._format_seconds(chunk_end)}"
                    ),
                    "segment_count": len(chunk_segments),
                }
            )

            if end_idx >= len(normalized_segments) - 1:
                break

            next_start_time = max(chunk_start + 0.001, chunk_end - overlap_duration)
            next_start_idx = end_idx + 1

            for idx in range(start_idx + 1, len(normalized_segments)):
                segment = normalized_segments[idx]
                segment_start = float(segment.get("start", 0.0))
                segment_end = float(segment.get("end", segment_start))

                if segment_end > next_start_time or segment_start >= next_start_time:
                    next_start_idx = idx
                    break

            if next_start_idx <= start_idx:
                next_start_idx = start_idx + 1

            start_idx = next_start_idx

        return chunks


if __name__ == "__main__":
    input_data = {
        "title": "TRUMP'S most CHAOTIC press conference ending has everyone SPEECHLESS",
        "uploader": "Diario AS",
        "upload_date": "20260406",
        "duration": 229,
        "view_count": 466269,
        "like_count": 6444,
        "dislike_count": None,
        "comment_count": 5100,
        'transcript': [{'text': 'Mr.', 'start': 0.0, 'duration': 3.2, 'end': 3.2, 'timecode': '00:00:00.000 --> 00:00:03.200'}, {'text': 'President, you voiced your displeasure with NATO in the past. Is there a danger to the US not being the de facto of the leader of the alliance and then other powers within the alliance then getting the decision-making when it comes to wars and nuclear weapons?', 'start': 0.8, 'duration': 4.84, 'end': 18.560000000000002, 'timecode': '00:00:00.800 --> 00:00:18.560'}, {'text': "it's not a danger. NATO's Look, we went to NATO.", 'start': 15.8, 'duration': 4.12, 'end': 21.919999999999998, 'timecode': '00:00:15.800 --> 00:00:21.920'}, {'text': "I didn't ask very strongly. I just said,", 'start': 19.92, 'duration': 3.6, 'end': 23.520000000000003, 'timecode': '00:00:19.920 --> 00:00:23.520'}, {'text': '"Hey, if you want to help, great." No, no, no, we will not help. I said,', 'start': 21.92, 'duration': 3.64, 'end': 26.6, 'timecode': '00:00:21.920 --> 00:00:26.600'}, {'text': '"That\'s all right. You don\'t want to help." Cuz I\'ve always said NATO is a paper tiger.', 'start': 25.56, 'duration': 3.2, 'end': 32.92, 'timecode': '00:00:25.560 --> 00:00:32.920'}, {'text': 'See, NATO is a paper tiger.', 'start': 30.36, 'duration': 4.36, 'end': 34.72, 'timecode': '00:00:30.360 --> 00:00:34.720'}, {'text': "Putin's not afraid of NATO. Putin's afraid of us, very afraid of us.", 'start': 32.92, 'duration': 4.32, 'end': 38.8, 'timecode': '00:00:32.920 --> 00:00:38.800'}, {'text': "And he's explained it to me a lot of times. I got to know him very well. I know him very well.", 'start': 37.24, 'duration': 3.32, 'end': 45.6, 'timecode': '00:00:37.240 --> 00:00:45.600'}, {'text': 'Uh NATO is a paper tiger. NATO is us.', 'start': 42.12, 'duration': 5.32, 'end': 47.44, 'timecode': '00:00:42.120 --> 00:00:47.440'}, {'text': "And when we needed them, but we didn't need them, by the way.", 'start': 45.6, 'duration': 3.52, 'end': 51.16, 'timecode': '00:00:45.600 --> 00:00:51.160'}, {'text': "We didn't need them, obviously, cuz they haven't helped at all. Just the opposite. They've actually gone out of their way not to help. They didn't even want to give us landing strips.", 'start': 49.12, 'duration': 3.68, 'end': 61.2, 'timecode': '00:00:49.120 --> 00:01:01.200'}, {'text': "Think of it. And it's not just NATO. You know who else didn't help us? South", 'start': 59.08, 'duration': 3.96, 'end': 65.08, 'timecode': '00:00:59.080 --> 00:01:05.080'}, {'text': "Korea didn't help us. You know who else didn't help us? Australia didn't help us. You know who else didn't help us?", 'start': 63.04, 'duration': 4.84, 'end': 71.8, 'timecode': '00:01:03.040 --> 00:01:11.800'}, {'text': 'Japan.', 'start': 69.84, 'duration': 5.2, 'end': 75.04, 'timecode': '00:01:09.840 --> 00:01:15.040'}, {'text': "We've got 50,000 soldiers in Japan to protect them from North Korea. We have 45,000 soldiers in South Korea to protect us from Kim Jong-un, who I get along with very well, as you know.", 'start': 71.8, 'duration': 5.24, 'end': 87.47999999999999, 'timecode': '00:01:11.800 --> 00:01:27.480'}, {'text': "Do you notice he said very nice things about me? He used to call uh Joe Biden a mentally person, okay? So, don't tell me about your stuff.", 'start': 85.84, 'duration': 4.36, 'end': 97.12, 'timecode': '00:01:25.840 --> 00:01:37.120'}, {'text': "Joe Biden, he said he's a mentally person. He was so nasty to Joe", 'start': 95.64, 'duration': 3.76, 'end': 101.4, 'timecode': '00:01:35.640 --> 00:01:41.400'}, {'text': "Biden. It was terrible. But to me, he likes Trump. And do you notice how nice things are with North Korea? It's very nice.", 'start': 99.4, 'duration': 4.84, 'end': 110.28, 'timecode': '00:01:39.400 --> 00:01:50.280'}, {'text': "But we have 45,000 people soldiers in harm's way and right next to Kim Jong-un with a lot of nuclear weapons.", 'start': 106.56, 'duration': 6.44, 'end': 117.6, 'timecode': '00:01:46.560 --> 00:01:57.600'}, {'text': "45 which should have never happened if a certain president, I'm not going to mention this president cuz I happen to like him, believe it or not. But if a certain president did his job, Kim", 'start': 115.08, 'duration': 4.68, 'end': 127.36, 'timecode': '00:01:55.080 --> 00:02:07.360'}, {'text': "Jong-un would not have nuclear weapons right now. But they're all afraid to do their job properly.", 'start': 125.56, 'duration': 3.4, 'end': 134.56, 'timecode': '00:02:05.560 --> 00:02:14.560'}, {'text': 'But just to conclude and just to finish,', 'start': 130.8, 'duration': 5.96, 'end': 136.76000000000002, 'timecode': '00:02:10.800 --> 00:02:16.760'}, {'text': "Japan didn't help us, Australia didn't help us, South Korea didn't help us. And then you get to NATO, NATO didn't help us. There were some countries that did.", 'start': 134.56, 'duration': 5.0, 'end': 145.52, 'timecode': '00:02:14.560 --> 00:02:25.520'}, {'text': "Now, countries that have been good, now you could also say they're got to be a little bit more involved because they're in the territory. But", 'start': 143.52, 'duration': 3.76, 'end': 152.64000000000001, 'timecode': '00:02:23.520 --> 00:02:32.640'}, {'text': "Saudi Arabia's been excellent. Qatar's been excellent. UAE has been excellent.", 'start': 150.2, 'duration': 5.6, 'end': 157.79999999999998, 'timecode': '00:02:30.200 --> 00:02:37.800'}, {'text': 'Bahrain, Kuwait, I mean, Kuwait did shoot down three of our planes. The only planes really that we lost were friendly fire, they called it. I call it unfriendly fire.', 'start': 155.8, 'duration': 4.36, 'end': 167.96, 'timecode': '00:02:35.800 --> 00:02:47.960'}, {'text': "They unfortunately didn't know how to use our our great Patriots.", 'start': 166.24, 'duration': 3.48, 'end': 173.84, 'timecode': '00:02:46.240 --> 00:02:53.840'}, {'text': 'The pilots said, "What kind of a missile\'s coming at us?" Patriot. Boom.', 'start': 172.6, 'duration': 3.56, 'end': 177.76, 'timecode': '00:02:52.600 --> 00:02:57.760'}, {'text': 'They got out.', 'start': 176.16, 'duration': 3.96, 'end': 180.12, 'timecode': '00:02:56.160 --> 00:03:00.120'}, {'text': 'Because they know Patriot never misses.', 'start': 177.76, 'duration': 4.68, 'end': 182.44, 'timecode': '00:02:57.760 --> 00:03:02.440'}, {'text': 'So, they had beautiful Patriots. There were planes heading in their direction.', 'start': 180.12, 'duration': 4.88, 'end': 187.24, 'timecode': '00:03:00.120 --> 00:03:07.240'}, {'text': 'Unfortunately, they decided to shoot those planes. They were our planes. So,', 'start': 185.0, 'duration': 4.8, 'end': 191.28, 'timecode': '00:03:05.000 --> 00:03:11.280'}, {'text': 'No, NATO is a paper tiger.', 'start': 191.28, 'duration': 4.28, 'end': 195.56, 'timecode': '00:03:11.280 --> 00:03:15.560'}, {'text': "Now, he's coming to see me on Wednesday, as you know. He's a wonderful guy.", 'start': 193.56, 'duration': 4.52, 'end': 200.36, 'timecode': '00:03:13.560 --> 00:03:20.360'}, {'text': 'Secretary General is great.', 'start': 198.08, 'duration': 4.28, 'end': 202.36, 'timecode': '00:03:18.080 --> 00:03:22.360'}, {'text': "And Mark Rutte is a great person, but he's got And you know, it all began with, if you want to know the truth,", 'start': 200.36, 'duration': 3.96, 'end': 209.24, 'timecode': '00:03:20.360 --> 00:03:29.240'}, {'text': 'Greenland.', 'start': 207.8, 'duration': 3.36, 'end': 211.16000000000003, 'timecode': '00:03:27.800 --> 00:03:31.160'}, {'text': 'We want Greenland. They don\'t want to give it to us and I said, "Bye-bye."', 'start': 209.24, 'duration': 4.84, 'end': 216.24, 'timecode': '00:03:29.240 --> 00:03:36.240'}, {'text': 'Okay, thank you very much, everybody.', 'start': 214.08, 'duration': 4.44, 'end': 218.52, 'timecode': '00:03:34.080 --> 00:03:38.520'}, {'text': 'Thank you.', 'start': 216.24, 'duration': 2.28, 'end': 218.52, 'timecode': '00:03:36.240 --> 00:03:38.520'}, {'text': 'What about rising gas prices for', 'start': 221.72, 'duration': 3.6, 'end': 225.32, 'timecode': '00:03:41.720 --> 00:03:45.320'}, {'text': 'Americans? What are your concerns?', 'start': 223.56, 'duration': 4.12, 'end': 227.68, 'timecode': '00:03:43.560 --> 00:03:47.680'}, {'text': 'General', 'start': 225.32, 'duration': 2.36, 'end': 227.68, 'timecode': '00:03:45.320 --> 00:03:47.680'}]}
    
    chunk = ChunkTranscript()
    result = chunk.invoke(input_data)
    print("result : ", result['transcript_chunks'][2])