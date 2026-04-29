""""
Transcript Cleaning Module,

It helps to clean the transcript data by removing unwanted characters, formatting issues, and other noise that may be present in the raw transcript. This module can be used to preprocess the transcript data before further analysis or enrichment.   

"""
from typing import Any
import re
class Cleaning:
    def __init__(self):
        self.JUNK_PATTERN = re.compile(r'\[(Music|Applause|Foreign language over loudspeaker)\]', re.IGNORECASE)
        self.SPEAKER_TAG = re.compile(r'^\s*>>\s*')  # Matches lines starting with ">>" (speaker tags)
        self.FILLER_ONLY = re.compile(r'^\s*(uh|um|ah|like|you know|so|actually|basically|I mean)\s*$', re.IGNORECASE)
    
    def invoke(self, segments: dict[str, Any]) -> dict[str, Any]:
        """
        Clean raw transcript segments.
    
        Handles:
        - Junk tags like [Music], [Applause], [Foreign language over loudspeaker]
        - Speaker prefixes like >>
        - Overlapping / rolling captions (deduplication by text similarity)
        - Broken mid-sentence caption merges
        - Whitespace normalization
        - Standalone filler segments (uh, um)
    
        Input / Output:
            [{"text": str, "start": float, "end": float, "timecode": str}]
        """
        
        transcript = segments.get('transcript', [])

        cleaned = []
    
        for seg in transcript:
            text = seg.get("text","")
            
            #1. Remove Junk Words
            text = self.JUNK_PATTERN.sub('', text)
            
            #2. Remove Speaker Tags
            text = self.SPEAKER_TAG.sub('', text)
    
            #3. Normalize whitespace
            text = re.sub(r'\s+', ' ', text).strip()
    
            #4. Drop empty or filler only segments
            if not text or self.FILLER_ONLY.match(text):
                continue
    
            cleaned.append({**seg, "text": text})
            
        #5. Remove Overlapping / Rolling captions (simple deduplication by text)
        deduped = []
        for i, seg in enumerate(cleaned):
            if i < len(cleaned) - 1:
                next_text = cleaned[i + 1]["text"].lower()
                curr_text = seg['text'].lower()
                #skip if current text is a leading substrng of the next segment
                if next_text.startswith(curr_text):
                    continue
            deduped.append(seg)            
        # 6. Merge broken captions (mid-sentence splits)
        merged = []
        for seg in deduped:
            if not merged:
                merged.append(dict(seg))
                continue
    
            prev = merged[-1]
            prev_text = prev["text"]
            curr_text = seg["text"]
    
            should_merge = (
                not re.search(r'[.!?]$', prev_text)       # prev has no end punctuation
                and curr_text[0].islower()                 # current starts lowercase
                and seg['start'] <= float(prev['end'])                   # close in time (< 1 second gap)
            )
    
            if should_merge:
                prev["text"] += " " + curr_text
                prev["end"]  = seg["end"]
                prev["timecode"] = (
                    prev["timecode"].split("-->")[0].strip()
                    + " --> "
                    + seg["timecode"].split("-->")[1].strip()
                )
            else:
                merged.append(dict(seg))
        segments['transcript'] = merged
        return segments
    
