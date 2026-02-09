import openai
import time
import re
import sys
import subprocess
import io
import shutil
from collections import deque
from datetime import datetime
import wave

# ========== FILE LOGGING SETUP ==========
LOG_FILE = "whisper_regex_llm_postdetection.txt"

class TeeOutput:
    """Class to write output to both console and file (append mode)"""
    def __init__(self, file_path):
        self.terminal = sys.stdout
        self.log_file = open(file_path, 'a', encoding='utf-8')
    
    def write(self, message):
        self.terminal.write(message)
        self.log_file.write(message)
        self.log_file.flush()  # Ensure immediate write
    
    def flush(self):
        self.terminal.flush()
        self.log_file.flush()
    
    def close(self):
        self.log_file.close()

# Redirect stdout to write to both console and file
tee = TeeOutput(LOG_FILE)
sys.stdout = tee

# ========== CONFIG ==========
OPENAI_API_KEY = "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"
# Set GAME_TYPE to "basketball" for basketball games or "football" for football games
GAME_TYPE = "football"  # Options: "basketball" or "football"
# Set DETECTION_MODE to "kickoff_tipoff" for game start detection or "halftime_resumption" for halftime resumption detection
DETECTION_MODE = "halftime_resumption"  # Options: "kickoff_tipoff" or "halftime_resumption"
# Set AUDIO_SOURCE_TYPE to "s3_url" for testing with S3 bucket audio clips, or "stream_url" for live streams
AUDIO_SOURCE_TYPE = "s3_url"  # Options: "s3_url" or "stream_url"
# For S3 URL: Use a publicly accessible S3 URL (e.g., "https://bucket-name.s3.region.amazonaws.com/path/to/audio.mp3")
# For Stream URL: Use a live stream URL (e.g., "https://img.leanstream.co/IM5001-MP3")
AUDIO_URL = "https://file-hosting-bucket-1.s3.us-east-1.amazonaws.com/FOOTBALL_duke-NCState_20min_HALFTIME.mp3?response-content-disposition=inline&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Security-Token=IQoJb3JpZ2luX2VjEMn%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIQCi9HDSTlOFWaKdK%2BSi5SNAUENyd48lAiJpgzwd%2F0miRgIgP0Op%2F%2B7GfZ2tw5SDThwxgMfBFMTc5imiZzlNU6G19ekq1QMIkv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw5ODkwNjE4NjQyNzciDGqqdYsg23P6Q9NdsyqpA%2FPbcrbN3lzqpV3qg6r30StTlcCl2aBTSp22fknB%2FOsY2j%2B66JVTnpEQt6DrygC3D4uBWb59jwZMeFTN1QKJODVs2Dt4LNtOzkEM7h4YUthvfi11QOzkeOffADkmj7jrqwxGa8dPBmgvgKmt1mk2%2FheJvcRsHm8QXn6pxH10yvNSzXg9sECITlhnypqubrGoMkdTF9qsYp%2FNkJaW%2BhH8oztZLUfpmvjONvLgz6vOGOpHF9ANAfsQoRiBE11bwdQk4MHEABNU64kldp2iIke%2FhqF29CRnA8HkUtZa261tUvtt7QfJmQ0OrnbjWWc2N5YLPWlqOEsWaEQRFFpR5nLceaADhXuKerFNLaCWa0ib7v5NdWJ34mb5%2FelYP6MhjylOcHj6iAsCTffxw%2BjkQPS%2F8xel71Qj%2FJBttd8VnQTe8aNIugUsg9QNaFZk03OMAtzv1J94IIgEVGJuUpC%2BxajvVpN9rzs4tyiyMvhcmQlniCfGn4a%2BMyS%2F1BdqYREJ225Q1ss3swsCn29m%2FpU6gh11LuEc8S8LbizCqq%2Br5bO98hQ65ukSCMFO%2BqTqMObOp8wGOt4CAQaDbsZDt0G2wR%2BlZFrwS2B50wlSKdzz4GUkoF73Tx2XteKBDCd8BXT8tVwhdkXOBrvTfZBSZGq9Fmd5G%2FyakjdQ2o5NZQBN6CNRCFMTC0J4JbiAPSr%2B%2BTGa1y5bMNfEce3XYmn9KwTMP6zR2h46LRQsakcJfp3CNDiStbh%2FxAatQqbx%2BYX387Zi%2B58kVIjBzpBnRSYReXLAE74IfY222yi55xTlTC7jp9qfIQT6JcEoWFjYfXcOQKDmCAflrbvNXxvh1r0IYnx026QMK3EP9i1yz6PA1Ibu1av1nKyG5DGDE%2FqgJD2cij7iegRl%2FHGP9TCLD%2F%2FzJ0Z1kOp11JeZiyfWNXN3s64LPIlc%2BYu3rp79p3x%2BcGCertqnM%2FFOwNiWVfYnaw24mWggdSCKOlBfaGZeBiC%2BUQB6Lep1FBWyVkoYSJnQIRqRyNnk8gAW3guVWPxFMlM%2FxMYDyKoz8Wo%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIA6MSFOLNKU2BD574S%2F20260209%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260209T162912Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=host&X-Amz-Signature=5210c75275130c3d767a9a78f1435e2a46311cf200a487e573cbd20315a99d01"  # Replace with your S3 URL
STREAM_URL = "https://img.leanstream.co/IM5001-MP3"  # Keep for future stream use
USE_LLM = "yes"

# Game type and detection mode configuration
GAME_EMOJI = "🏀" if GAME_TYPE == "basketball" else "🏈"
GAME_NAME = "Basketball" if GAME_TYPE == "basketball" else "Football"

# Set event name based on game type and detection mode
if DETECTION_MODE == "halftime_resumption":
    GAME_EVENT = "halftime resumption"
    if GAME_TYPE == "basketball":
        DETECTOR_TITLE = f"{GAME_EMOJI} {GAME_NAME} Halftime Resumption Detector"
    else:
        DETECTOR_TITLE = f"{GAME_EMOJI} {GAME_NAME} Halftime Resumption Detector"
else:  # kickoff_tipoff
    GAME_EVENT = "tip-off" if GAME_TYPE == "basketball" else "kickoff"
    if GAME_TYPE == "basketball":
        DETECTOR_TITLE = f"{GAME_EMOJI} {GAME_NAME} Tip-Off Detector"
    else:
        DETECTOR_TITLE = f"{GAME_EMOJI} {GAME_NAME} Kickoff Detector"

print(DETECTOR_TITLE)
print("=" * 60)
print(f"📝 Logging started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Audio settings
SAMPLE_RATE = 16000
CHUNK_DURATION = 2.0  # seconds - process every 2 seconds of audio
CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION * 2)  # 2 bytes per sample (16-bit)
CONFIRMATION_DURATION = 8.0  # seconds - collect 8 seconds after detection for confirmation
CONFIRMATION_CHUNK_SIZE = int(SAMPLE_RATE * CONFIRMATION_DURATION * 2)

openai.api_key = OPENAI_API_KEY

# ========== STATE ==========
tipoff_detected = False
tipoff_confirmed = False
sentence_buffer = deque(maxlen=5)
all_sentences = []
stream_start_time = None
sentence_index = 0
current_sentence = ""
silence_counter = 0

# ========== FAST KEYWORD CHECK ==========
def fast_keyword_check(text):
    """Quick regex check with REJECTION patterns"""
    text_lower = text.lower()
    
    # REJECT patterns (future tense indicators) - common for both sports
    reject_patterns = [
        r'\b(moments?|seconds?|minutes?)\s+away\b',
        r'\b(coming|about to|will|going to|ready to)\s+(start|tip|kick|begin)\b',
        r'\bwill\s+(tip\s*off|kick\s*off)\b',
        r'\babout\s+to\s+(get\s+)?(underway|start)\b',
        r'\bcoming\s+up\b.*\b(tip|kick)\b',
        r'\bget\s+ready\b',
        r'\balmost\s+time\b',
        r'\bshortly\b',
        r'\bin\s+just\s+a\s+(moment|second|minute)\b',
        r'\blet\'?s\s+go\b(?!.*\b(controlled?|won|gets?|received?|returns?)\b)',  # "let's go" without action words
        r'^(on\.?\s*)?(go!?|let\'?s go!?)$',  # Just "on. Go!" or "Go!" or "Let's go!"
    ]
    
    for pattern in reject_patterns:
        if re.search(pattern, text_lower):
            return "REJECT"
    
    # High-confidence patterns (PAST tense - already happened)
    if DETECTION_MODE == "halftime_resumption":
        # Halftime resumption patterns
        if GAME_TYPE == "basketball":
            high_confidence = [
                r'\b(second\s+half|second\s+period)\s+.*\b(underway|begins?|starts?)\b',
                r'\b(back|resume|resuming)\s+.*\b(second\s+half|action|play)\b',
                r'\b(second\s+half|second\s+period)\s+.*\b(controlled|won|gets?|got)\s+(the\s+)?(tip|tap)\b',
                r'\b(controlled|controls|won|wins|gets|got)\s+the\s+(second\s+half\s+)?(tip|tap)\b',
                r'\baway\s+we\s+go\b.*\b(second\s+half|second\s+period)\b',
                r'\b(second\s+half|second\s+period)\s+.*\b(underway|begins?|starts?)\b',
                r'\b(he|she|they)\s+(controls?|wins?|gets?|got)\s+(it|the\s+tip)\b.*\b(second\s+half|second\s+period)\b',
            ]
        else:  # football
            high_confidence = [
                r'\b(second\s+half|third\s+quarter)\s+.*\b(underway|begins?|starts?)\b',
                r'\b(back|resume|resuming)\s+.*\b(second\s+half|third\s+quarter|action|play)\b',
                r'\b(second\s+half|third\s+quarter)\s+.*\b(kickoff|kick)\b.*\b(received|returns?|taken|fielded)\b',
                r'\b(kickoff|kick)\s+.*\b(second\s+half|third\s+quarter)\b.*\b(received|returns?|fielded)\b',
                r'\b(he|she|they|team)\s+(receives?|received|returns?|returned|fields?|fielded)\s+(the\s+)?(kickoff|kick)\b.*\b(second\s+half|third\s+quarter)\b',
                r'\baway\s+we\s+go\b.*\b(second\s+half|third\s+quarter)\b',
            ]
    else:  # kickoff_tipoff
        if GAME_TYPE == "basketball":
            high_confidence = [
                r'\b(controlled|controls|won|wins|gets|got)\s+the\s+(opening\s+)?(tip|tap)\b',
                r'\bopening\s+(tip|tap)\b.*\b(controlled|won|goes to|got)\b',
                r'\btip\s*off\b.*\bunderway\b',
                r'\baway\s+we\s+go\b.*\b(tip|tap|controlled?|won)\b',
                r'\bball\s+(is\s+)?(tossed|up)\b.*\b(controlled|won|got)\b',
                r'\b(he|she|they)\s+(controls?|wins?|gets?|got)\s+(it|the\s+tip)\b',
                r'\bstarts\s+with\s+\w+\s+(winning|wins|gets?|got)\s+the\s+(tip|tap)\b',
            ]
        else:  # football
            high_confidence = [
                r'\b(kickoff|kick\s*off)\s+.*\b(underway|begins?|starts?)\b',
                r'\b(opening\s+)?kickoff\b.*\b(received|returns?|taken|fielded)\b',
                r'\baway\s+we\s+go\b.*\b(kickoff|kick|received?|returns?)\b',
                r'\b(kicked|kicks?)\s+(off|the\s+ball)\b.*\b(received|returns?|fielded)\b',
                r'\b(he|she|they|team)\s+(receives?|received|returns?|returned|fields?|fielded)\s+(the\s+)?(kickoff|kick)\b',
                r'\b(kickoff|kick)\s+(is\s+)?(received|returned|fielded)\b',
                r'\bstarts\s+with\s+.*\b(kickoff|kick)\b',
            ]
    
    for pattern in high_confidence:
        if re.search(pattern, text_lower):
            return "HIGH"
    
    # Medium-confidence patterns
    if DETECTION_MODE == "halftime_resumption":
        if GAME_TYPE == "basketball":
            medium_confidence = [
                r'\b(second\s+half|second\s+period)\b',
                r'\baway\s+we\s+go\b',
                r'\bhere\s+we\s+go\b',
                r'\bunderway\b',
                r'\b(back|resume|resuming)\b',
            ]
        else:  # football
            medium_confidence = [
                r'\b(second\s+half|third\s+quarter)\b',
                r'\baway\s+we\s+go\b',
                r'\bhere\s+we\s+go\b',
                r'\bunderway\b',
                r'\b(back|resume|resuming)\b',
            ]
    else:  # kickoff_tipoff
        if GAME_TYPE == "basketball":
            medium_confidence = [
                r'\baway\s+we\s+go\b',
                r'\bhere\s+we\s+go\b',
                r'\bunderway\b',
                r'\bjump\s+ball\b',
            ]
        else:  # football
            medium_confidence = [
                r'\baway\s+we\s+go\b',
                r'\bhere\s+we\s+go\b',
                r'\bunderway\b',
                r'\b(kickoff|kick\s*off)\b',
            ]
    
    for pattern in medium_confidence:
        if re.search(pattern, text_lower):
            return "MEDIUM"
    
    return "LOW"

# ========== PRE-CONTEXT VERIFICATION ==========
def verify_pre_context(context_sentences):
    """
    Verify that preceding segments contain pre-event indicators (moments away, about to start, etc.)
    Returns True if pre-context suggests the event is about to happen or just happened.
    """
    if not context_sentences or len(context_sentences) < 2:
        return True  # Not enough context, don't reject
    
    # Check preceding sentences (excluding current)
    preceding_text = " ".join(context_sentences[:-1]).lower()
    
    # Pre-event indicators (good signs - event is approaching or just happened)
    pre_event_indicators = [
        r'\b(moments?|seconds?|minutes?)\s+away\b',
        r'\b(coming|about to|ready to)\s+(start|tip|kick|begin)\b',
        r'\babout\s+to\s+(get\s+)?(underway|start)\b',
        r'\b(get\s+ready|almost\s+time|shortly)\b',
        r'\b(away|here)\s+we\s+go\b',
        r'\bunderway\b',
    ]
    
    # Check if any pre-event indicators exist
    for pattern in pre_event_indicators:
        if re.search(pattern, preceding_text):
            return True
    
    # If no pre-event indicators but also no strong rejection patterns, allow it
    return True

# ========== GAMEPLAY CONFIRMATION CHECK ==========
def confirm_gameplay(confirmation_text, initial_detection_text):
    """
    Analyze the audio following the initial detection to confirm it's actual gameplay.
    Returns True if the following audio contains gameplay indicators AND post-event context.
    """
    try:
        start_time = time.time()
        
        # Build mode-specific and sport-specific prompts
        if DETECTION_MODE == "halftime_resumption":
            if GAME_TYPE == "basketball":
                analyst_type = "basketball analyst"
                event_name = "halftime resumption"
                gameplay_indicators = """- Player names + action verbs (shoots, passes, dribbles, drives, scores, misses, rebounds, blocks, steals)
- Shot clock mentions
- Score updates
- Foul calls
- Possession descriptions
- Court positions (baseline, three-point line, paint, elbow, wing)
- Defensive actions (guards, defends, switches, helps)
- Play-by-play commentary of live action
- Second half/second period gameplay"""
                examples = """✅ "Smith drives left, pulls up, shoots... good!" → YES (gameplay)
✅ "Rebound goes to Johnson, outlet pass to Williams" → YES (gameplay)
✅ "Foul on number 23, that's his second" → YES (gameplay)
✅ "Second half underway, Smith controls the tip" → YES (gameplay)
❌ "Halftime analysis continues" → NO (halftime break)
❌ "Coming up after the break" → NO (still in break)
❌ "Let's go! Here we go!" → NO (hype, not gameplay)"""
            else:  # football
                analyst_type = "football analyst"
                event_name = "halftime resumption"
                gameplay_indicators = """- Player names + action verbs (runs, throws, passes, catches, tackles, scores, fumbles, intercepts)
- Down and distance mentions
- Score updates
- Penalty calls
- Possession descriptions
- Field positions (end zone, red zone, midfield, sideline, hash marks)
- Defensive actions (tackles, sacks, coverage, blitzes)
- Play-by-play commentary of live action
- Second half/third quarter gameplay"""
                examples = """✅ "Smith takes the handoff, breaks left, gains 5 yards" → YES (gameplay)
✅ "Johnson throws deep, caught by Williams for a touchdown!" → YES (gameplay)
✅ "Penalty on the defense, 15 yards" → YES (gameplay)
✅ "Second half underway, kickoff received" → YES (gameplay)
❌ "Halftime analysis continues" → NO (halftime break)
❌ "Coming up after the break" → NO (still in break)
❌ "Let's go! Here we go!" → NO (hype, not gameplay)"""
        else:  # kickoff_tipoff
            if GAME_TYPE == "basketball":
                analyst_type = "basketball analyst"
                event_name = "tip-off"
                gameplay_indicators = """- Player names + action verbs (shoots, passes, dribbles, drives, scores, misses, rebounds, blocks, steals)
- Shot clock mentions
- Score updates
- Foul calls
- Possession descriptions
- Court positions (baseline, three-point line, paint, elbow, wing)
- Defensive actions (guards, defends, switches, helps)
- Play-by-play commentary of live action"""
                examples = """✅ "Smith drives left, pulls up, shoots... good!" → YES (gameplay)
✅ "Rebound goes to Johnson, outlet pass to Williams" → YES (gameplay)
✅ "Foul on number 23, that's his second" → YES (gameplay)
❌ "Starting at guard, number 5, John Smith" → NO (pre-game)
❌ "The crowd is on their feet, ready for tip-off" → NO (pre-game)
❌ "Let's go! Here we go!" → NO (pre-game hype)"""
            else:  # football
                analyst_type = "football analyst"
                event_name = "kickoff"
                gameplay_indicators = """- Player names + action verbs (runs, throws, passes, catches, tackles, scores, fumbles, intercepts)
- Down and distance mentions
- Score updates
- Penalty calls
- Possession descriptions
- Field positions (end zone, red zone, midfield, sideline, hash marks)
- Defensive actions (tackles, sacks, coverage, blitzes)
- Play-by-play commentary of live action"""
                examples = """✅ "Smith takes the handoff, breaks left, gains 5 yards" → YES (gameplay)
✅ "Johnson throws deep, caught by Williams for a touchdown!" → YES (gameplay)
✅ "Penalty on the defense, 15 yards" → YES (gameplay)
❌ "Starting at quarterback, number 5, John Smith" → NO (pre-game)
❌ "The crowd is on their feet, ready for kickoff" → NO (pre-game)
❌ "Let's go! Here we go!" → NO (pre-game hype)"""
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an expert {analyst_type}. Your job is to determine if the audio following a potential {event_name} detection contains ACTUAL GAMEPLAY or if it's still PRE-GAME/HALFTIME TALK.

{"="*60}
CRITICAL FOR HALFTIME RESUMPTION - STRICT VERIFICATION:
{"="*60}

FIRST: Reject if following audio is HALFTIME ANALYSIS/COMMENTARY:
- "halftime", "at halftime", "halftime score", "halftime analysis", "halftime coverage"
- Statistics, scores, or analysis without gameplay action
- "coming up", "after the break", "moments away"
- Just announcements without actual player actions
→ If any of these, answer NO immediately

SECOND: Accept ONLY if following audio has CLEAR GAMEPLAY:
- Player names + action verbs (shoots, passes, runs, throws, tackles, etc.)
- Actual play-by-play commentary of live action
- Score updates during gameplay
- Fouls, penalties, or game events happening NOW
- NOT just "underway" or "away we go" - must have actual gameplay

GAMEPLAY INDICATORS (answer YES - must have actual player actions):
{gameplay_indicators}

PRE-GAME/HALFTIME INDICATORS (answer NO):
- Lineup announcements
- Player introductions
- Starting lineup discussions
- Uniform descriptions
- Pre-game/halftime statistics
- "Coming up", "about to start", "moments away"
- Sponsor mentions
- Stadium/crowd descriptions without action
- Coach/season background info
- Halftime analysis or commentary (STRICT REJECTION)
- Just crowd noise or music
- Just "underway" or "away we go" without gameplay action

EXAMPLES:
{examples}

Answer ONLY: YES or NO"""
                },
                {
                    "role": "user",
                    "content": f"""Initial detection: "{initial_detection_text}"

Following audio (next 8 seconds):
"{confirmation_text}"

QUESTION: Does the following audio contain ACTUAL GAMEPLAY (player actions, shots, passes, fouls, etc.) AND does it show POST-{event_name.upper()} context (game has started/resumed, action is happening)?

{"="*60}
CRITICAL FOR HALFTIME RESUMPTION - STRICT VERIFICATION:
{"="*60}

FIRST: Reject if following audio is HALFTIME ANALYSIS/COMMENTARY:
- "halftime", "at halftime", "halftime score", "halftime analysis"
- Statistics, scores, or analysis without gameplay action
- "coming up", "after the break"
→ If any of these, answer NO immediately

SECOND: Accept ONLY if following audio has BOTH:
1. CLEAR gameplay indicators: Player names + action verbs (shoots, passes, runs, throws, tackles, etc.)
2. POST-event context: Game underway, action happening, NOT pre-game/halftime talk
3. NOT just announcements: Must have actual player actions, not just "underway" or "away we go"

CRITICAL: Verify BOTH conditions are met:
1. Does it contain gameplay indicators? (player actions, scores, fouls, etc.) → Must be YES
2. Does it show POST-event context? (game underway, action happening, not pre-game/halftime talk) → Must be YES
3. Is it halftime analysis/commentary? → If YES, answer NO

Answer ONLY: YES or NO"""
                }
            ],
            temperature=0.0,
            max_tokens=10
        )
        
        elapsed = time.time() - start_time
        answer = response.choices[0].message.content.strip().upper()
        
        print(f"      🔍 Gameplay confirmation: {answer} (took {elapsed*1000:.0f}ms)")
        
        return 'YES' in answer
        
    except Exception as e:
        print(f"      ⚠️  Confirmation error: {e}")
        return False

# ========== ENHANCED LLM CONFIRMATION ==========
def llm_confirm(text, context_sentences, timestamp_ms, sentence_index):
    """Use GPT-4o-mini with rich context for validation"""
    try:
        # Build context with timestamps
        context_with_time = []
        for i, s in enumerate(context_sentences):
            if s:
                relative_pos = i - len(context_sentences) + 1
                if relative_pos == 0:
                    context_with_time.append(f"→ CURRENT: {s}")
                else:
                    context_with_time.append(f"  [{relative_pos}]: {s}")
        
        context_str = "\n".join(context_with_time)
        
        timestamp_sec = timestamp_ms / 1000
        minutes = int(timestamp_sec // 60)
        seconds = int(timestamp_sec % 60)
        
        start_time = time.time()
        
        # Build mode-specific and sport-specific detection prompts
        if DETECTION_MODE == "halftime_resumption":
            if GAME_TYPE == "basketball":
                analyst_type = "basketball analyst"
                event_name = "halftime resumption (second half/second period tip-off)"
                event_term = "halftime resumption"
                accept_examples = """✅ "Second half underway, Johnson controls the tip" → YES (clear resumption + action)
✅ "Back to action, Smith gets the second half tip" → YES (clear resumption + action)
✅ "Second period begins, Johnson controls the tip" → YES (clear resumption + action)
✅ "We're back, Smith wins the second half tip" → YES (clear resumption + action)"""
                accept_patterns = """STRICT REQUIREMENTS - ALL must be true:
1. MUST mention "second half/second period" OR "back to action/resuming play" 
2. MUST describe actual tip-off action: "controls/wins/gets the tip" OR "tip-off" + "underway/begins"
3. MUST be past/present tense (action completed or happening NOW)
4. MUST NOT be just "away we go" or "underway" alone - must have tip-off action"""
                reject_examples = """❌ "Second half is moments away" → NO (future tense)
❌ "About to resume after halftime" → NO (future tense)
❌ "Will start the second half shortly" → NO (future tense)
❌ "Halftime analysis continues" → NO (still in break)
❌ "Coming up after the break" → NO (still in break)
❌ "Away we go" → NO (no tip-off action described)
❌ "Second half underway" → NO (no tip-off action, just announcement)
❌ "Here we go" → NO (no tip-off action)
❌ "Back to action" → NO (no tip-off action described)
❌ "Halftime score is 45-40" → NO (halftime analysis)
❌ "At halftime, Duke leads" → NO (halftime analysis)
❌ "Welcome to halftime" → NO (halftime break)"""
                completed_actions = "controlled, won, got"
                ongoing_actions = "controls, wins, gets"
            else:  # football
                analyst_type = "football analyst"
                event_name = "halftime resumption (second half/third quarter kickoff)"
                event_term = "halftime resumption"
                accept_examples = """✅ "Second half underway, Johnson receives the kickoff" → YES (clear resumption + action)
✅ "Back to action, Smith returns the second half kick" → YES (clear resumption + action)
✅ "Third quarter begins, Johnson receives the kickoff" → YES (clear resumption + action)
✅ "We're back, Smith fields the kickoff" → YES (clear resumption + action)"""
                accept_patterns = """STRICT REQUIREMENTS - ALL must be true:
1. MUST mention "second half/third quarter" OR "back to action/resuming play"
2. MUST describe actual kickoff action: "receives/returns/fields the kickoff" OR "kickoff" + "underway/begins"
3. MUST be past/present tense (action completed or happening NOW)
4. MUST NOT be just "away we go" or "underway" alone - must have kickoff action"""
                reject_examples = """❌ "Second half is moments away" → NO (future tense)
❌ "About to resume after halftime" → NO (future tense)
❌ "Will start the second half shortly" → NO (future tense)
❌ "Halftime analysis continues" → NO (still in break)
❌ "Coming up after the break" → NO (still in break)
❌ "Away we go" → NO (no kickoff action described)
❌ "Second half underway" → NO (no kickoff action, just announcement)
❌ "Here we go" → NO (no kickoff action)
❌ "Back to action" → NO (no kickoff action described)
❌ "Halftime score is 21-14" → NO (halftime analysis)
❌ "At halftime, Duke leads" → NO (halftime analysis)
❌ "Welcome to halftime" → NO (halftime break)"""
                completed_actions = "received, returned, fielded, got"
                ongoing_actions = "receives, returns, fields"
        else:  # kickoff_tipoff
            if GAME_TYPE == "basketball":
                analyst_type = "basketball analyst"
                event_name = "tip-off or jump ball"
                event_term = "tip-off"
                accept_examples = """✅ "Johnson controls the opening tip" → YES (past tense, completed action)
✅ "Away we go, Smith gets it" → YES (present tense, happening now)
✅ "And we're underway" → YES (present tense, started)"""
                accept_patterns = """- "controls the tip", "wins the opening tap", "gets the tip"
- "away we go" (when game is starting, not pre-game)
- "underway" (when game has started, not "about to get underway")
- Player names + action verbs (e.g., "Smith controls it")
- Ball possession established after tip"""
                reject_examples = """❌ "Opening tip is moments away" → NO (future tense)
❌ "About to get underway" → NO (future tense)
❌ "Will tip off shortly" → NO (future tense)"""
                completed_actions = "controlled, won, got"
                ongoing_actions = "controls, gets, underway"
            else:  # football
                analyst_type = "football analyst"
                event_name = "kickoff"
                event_term = "kickoff"
                accept_examples = """✅ "Johnson receives the opening kickoff" → YES (past tense, completed action)
✅ "Away we go, Smith returns it" → YES (present tense, happening now)
✅ "And we're underway" → YES (present tense, started)"""
                accept_patterns = """- "receives the kickoff", "returns the kick", "fields the kickoff"
- "away we go" (when game is starting, not pre-game)
- "underway" (when game has started, not "about to get underway")
- Player names + action verbs (e.g., "Smith returns it")
- Ball possession established after kickoff"""
                reject_examples = """❌ "Opening kickoff is moments away" → NO (future tense)
❌ "About to get underway" → NO (future tense)
❌ "Will kick off shortly" → NO (future tense)"""
                completed_actions = "received, returned, fielded, got"
                ongoing_actions = "receives, returns, fields, underway"
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": f"""You are an expert {analyst_type} detecting the EXACT moment a {event_name} COMPLETES and (not when it's about to happen).

CRITICAL: You must distinguish between FUTURE and PRESENT/PAST tense.

❌ REJECT these (future tense - hasn't happened yet):
- "moments away", "seconds away", "coming up"
- "about to start", "will {event_term}", "going to begin"
- "get ready", "almost time", "shortly"
- "coming up next", "in just a moment"
- "Let's go!" or "Go!" without any action description
- ANY phrase indicating the {event_term} will happen soon but hasn't yet
- Halftime analysis or break commentary (if detecting halftime resumption)

✅ ACCEPT only these (present/past tense - happening NOW or just happened):
{accept_patterns}

EXAMPLES:
{reject_examples}
❌ "On. Go!" → NO (no action described)
❌ "Let's go!" → NO (hype, not action)
{accept_examples}

Answer ONLY: YES or NO"""
                },
                {
                    "role": "user",
                    "content": f"""Timeline: {minutes}:{seconds:02d} into broadcast

Recent conversation (PRE-context):
{context_str}

QUESTION: Has the {event_term} ALREADY HAPPENED or is HAPPENING RIGHT NOW in the current sentence?

{"="*60}
CRITICAL FOR HALFTIME RESUMPTION - STRICT VERIFICATION:
{"="*60}

FIRST: Reject if CURRENT sentence is HALFTIME ANALYSIS/COMMENTARY:
- "halftime", "at halftime", "halftime score", "halftime analysis"
- Statistics, scores, or analysis without gameplay action
- "coming up", "after the break", "moments away"
- Just "away we go", "here we go", "underway" WITHOUT tip-off/kickoff action
→ If any of these, answer NO immediately

SECOND: Accept ONLY if CURRENT sentence has BOTH:
1. Clear resumption indicator: "second half/second period/third quarter" OR "back to action/resuming play"
2. Actual event action: tip-off/kickoff action described (controls/wins/gets tip OR receives/returns/fields kickoff)
3. Past/present tense (not future)

Critical checks (in order):
1. Is CURRENT sentence halftime analysis/commentary? → If YES, answer NO
2. Does CURRENT sentence say "moments away", "coming up", "about to", "will", "going to"? → If YES, answer NO
3. Is CURRENT sentence just "Go!", "Let's go!", "Away we go", "Here we go", or "Underway" WITHOUT tip-off/kickoff action? → If YES, answer NO
4. Does CURRENT sentence have BOTH resumption indicator AND tip-off/kickoff action? → If NO, answer NO
5. Does CURRENT sentence describe a COMPLETED action ({completed_actions})? → If YES, check if it also has resumption indicator, then answer YES
6. Does CURRENT sentence describe ONGOING action ({ongoing_actions})? → If YES, check if it also has resumption indicator, then answer YES
7. Is CURRENT sentence talking about the FUTURE? → If YES, answer NO

Answer ONLY: YES or NO"""
                }
            ],
            temperature=0.0,
            max_tokens=10
        )
        
        elapsed = time.time() - start_time
        answer = response.choices[0].message.content.strip().upper()
        
        print(f"      LLM response: {answer} (took {elapsed*1000:.0f}ms)")
        
        return 'YES' in answer
        
    except Exception as e:
        print(f"      ⚠️  LLM error: {e}")
        return False

# ========== SENTENCE BOUNDARY DETECTION ==========
def is_sentence_boundary(text):
    """Check if text ends with sentence-ending punctuation"""
    text = text.strip()
    if not text:
        return False
    return text[-1] in '.!?'

# ========== DETECTION LOGIC ==========
def process_sentence(text, timestamp_ms, sentence_index):
    global tipoff_detected, sentence_buffer, all_sentences
    
    if tipoff_detected:
        return False
    
    sentence_buffer.append(text)
    all_sentences.append(text)
    
    # Skip very early sentences (likely pre-game)
    # if timestamp_ms < 30000:  # Skip first 30 seconds
        # return False
    
    # Fast keyword check
    confidence = fast_keyword_check(text)
    print(f"   🔍 For sentence: {text}, Fast keyword check: {confidence}")
    confidence = "HIGH" # For bypassing the fast keyword check
    # Immediate rejection
    if confidence == "REJECT":
        print(f"      ❌ Auto-rejected (future tense or hype phrase detected)")
        return False
    
    if confidence == "HIGH":
        # Even HIGH confidence should be validated if it's early in broadcast
        if USE_LLM == "yes":
            print(f"   🤔 High confidence but still, validating with LLM...")
            
            if not llm_confirm(text, list(sentence_buffer), timestamp_ms, sentence_index):
                print(f"      ❌ LLM rejected (likely pre-game talk)")
                return False
        
        # STAGE 1 PASSED - Mark as detected but not confirmed yet
        tipoff_detected = True
        timestamp_sec = timestamp_ms / 1000
        minutes = int(timestamp_sec // 60)
        seconds = int(timestamp_sec % 60)
        
        print("\n" + "="*60)
        print(f"🟡 POTENTIAL {GAME_EVENT.upper().replace('-', ' ')} at {minutes}:{seconds:02d}")
        print(f"   Detection: Fast keyword match (HIGH confidence)")
        print(f"   Text: {text}")
        print(f"   ⏳ Collecting next {CONFIRMATION_DURATION}s for gameplay confirmation...")
        print("="*60 + "\n")
        return True
    
    elif confidence == "MEDIUM" and USE_LLM == "yes":
        print(f"   🤔 Medium confidence, checking with LLM...")
        
        if llm_confirm(text, list(sentence_buffer), timestamp_ms, sentence_index):
            # STAGE 1 PASSED - Mark as detected but not confirmed yet
            tipoff_detected = True
            timestamp_sec = timestamp_ms / 1000
            minutes = int(timestamp_sec // 60)
            seconds = int(timestamp_sec % 60)
            
            print("\n" + "="*60)
            print(f"🟡 POTENTIAL {GAME_EVENT.upper().replace('-', ' ')} at {minutes}:{seconds:02d}")
            print(f"   Detection: LLM confirmed")
            print(f"   Text: {text}")
            print(f"   ⏳ Collecting next {CONFIRMATION_DURATION}s for gameplay confirmation...")
            print("="*60 + "\n")
            return True
        else:
            print(f"      ❌ LLM says NO")
    
    return False

# ========== TRANSCRIBE AUDIO CHUNK ==========
def transcribe_chunk(audio_data):
    """Transcribe a chunk of audio using OpenAI Whisper API"""
    try:
        # Create WAV file in memory
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(audio_data)
        
        wav_buffer.seek(0)
        wav_buffer.name = "audio.wav"
        
        # Transcribe with Whisper
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=wav_buffer,
            language="en"
        )
        
        return transcript.text.strip()
    except Exception as e:
        print(f"⚠️  Transcription error: {e}")
        return ""

# ========== CHECK FFMPEG AVAILABILITY ==========
def check_ffmpeg():
    """Check if ffmpeg is installed and available in PATH"""
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path is None:
        print("\n" + "="*60)
        print("❌ ERROR: ffmpeg is not installed or not in your system PATH")
        print("="*60)
        print("\n📥 To install ffmpeg on Windows:")
        print("   1. Download from: https://ffmpeg.org/download.html")
        print("   2. Or use chocolatey: choco install ffmpeg")
        print("   3. Or use winget: winget install ffmpeg")
        print("   4. Make sure to add ffmpeg to your system PATH")
        print("\n💡 After installation, restart your terminal/IDE and try again.")
        print("="*60 + "\n")
        return False
    else:
        print(f"✅ ffmpeg found at: {ffmpeg_path}")
        return True

# ========== AUDIO STREAMING ==========
def stream_audio():
    """Stream audio from URL (S3 or live stream) via ffmpeg and transcribe in chunks"""
    global stream_start_time, sentence_index, current_sentence, tipoff_confirmed, tipoff_detected
    
    # Check if ffmpeg is available
    if not check_ffmpeg():
        return
    
    # Determine which URL to use based on source type
    if AUDIO_SOURCE_TYPE == "s3_url":
        audio_url = AUDIO_URL
        source_description = f"S3 audio file: {audio_url}"
    else:
        audio_url = STREAM_URL
        source_description = f"Live stream: {audio_url}"
    
    print(f"\n🌐 Connecting to {source_description}\n")
    
    ffmpeg_cmd = [
        'ffmpeg',
        '-i', audio_url,
        '-f', 's16le',
        '-ar', str(SAMPLE_RATE),
        '-ac', '1',
        '-'
    ]
    
    try:
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=CHUNK_SIZE
        )
        
        stream_start_time = time.time()
        if AUDIO_SOURCE_TYPE == "s3_url":
            print(f"📁 Audio file loaded")
        else:
            print(f"🔴 Stream connected")
        print(f"🎧 Listening for {GAME_EVENT} (processing {CHUNK_DURATION}s chunks)...\n")
        
        detection_text = ""
        
        while not tipoff_confirmed:
            # Read chunk of audio
            audio_chunk = process.stdout.read(CHUNK_SIZE)
            if not audio_chunk or len(audio_chunk) < CHUNK_SIZE:
                break
            
            # Calculate timestamp
            elapsed_ms = int((time.time() - stream_start_time) * 1000)
            timestamp_sec = elapsed_ms / 1000
            minutes = int(timestamp_sec // 60)
            seconds = int(timestamp_sec % 60)
            
            # Transcribe chunk
            transcription_start = time.time()
            text = transcribe_chunk(audio_chunk)
            transcription_time = (time.time() - transcription_start) * 1000
            
            if text:
                # Accumulate text into sentences
                # current_sentence += " " + text
                current_sentence = text
                # current_sentence = current_sentence.strip()
                
                # Check if we have a complete sentence
                # if is_sentence_boundary(current_sentence):
                if True:  # Process every chunk as a sentence
                    # confidence = fast_keyword_check(current_sentence)
                    # confidence_emoji = {"HIGH": "🔥", "MEDIUM": "🤔", "LOW": "⚪", "REJECT": "🚫"}
                    
                    # print(f"[{minutes}:{seconds:02d}] {confidence_emoji[confidence]} {current_sentence} (transcribed in {transcription_time:.0f}ms)")
                    
                    # STAGE 1: Initial detection
                    if not tipoff_detected:
                        if process_sentence(current_sentence, elapsed_ms, sentence_index):
                            detection_text = current_sentence
                        sentence_index += 1
                    
                    # STAGE 2: Confirmation phase
                    elif tipoff_detected and not tipoff_confirmed:
                        # Collect next 8 seconds of audio for confirmation
                        print(f"   📝 Collecting confirmation audio...")
                        confirmation_audio = audio_chunk
                        
                        # Read additional chunks to get full confirmation duration
                        remaining_chunks = int(CONFIRMATION_DURATION / CHUNK_DURATION) - 1
                        for _ in range(remaining_chunks):
                            next_chunk = process.stdout.read(CHUNK_SIZE)
                            if next_chunk and len(next_chunk) == CHUNK_SIZE:
                                confirmation_audio += next_chunk
                        
                        # Transcribe confirmation audio
                        print(f"   🔍 Transcribing confirmation audio...")
                        confirmation_text = transcribe_chunk(confirmation_audio)
                        
                        print(f"   📄 Confirmation text: {confirmation_text}")
                        
                        # Check if following audio contains gameplay
                        if confirm_gameplay(confirmation_text, detection_text):
                            tipoff_confirmed = True
                            print("\n" + "="*60)
                            print(f"✅ {GAME_EVENT.upper().replace('-', ' ')} CONFIRMED!")
                            print(f"   Initial detection: {detection_text}")
                            print(f"   Gameplay confirmed in following audio")
                            print("="*60 + "\n")
                        else:
                            print("\n" + "="*60)
                            print(f"❌ FALSE POSITIVE REJECTED")
                            print(f"   Initial detection: {detection_text}")
                            print(f"   No gameplay found in following audio (likely pre-game hype)")
                            print(f"   Continuing to monitor...")
                            print("="*60 + "\n")
                            # Reset detection to continue monitoring
                            tipoff_detected = False
                    
                    # Reset sentence buffer
                    current_sentence = ""
        
        process.terminate()
        process.wait()
        
    except FileNotFoundError:
        print("\n" + "="*60)
        print("❌ ERROR: ffmpeg executable not found")
        print("="*60)
        print("\n📥 Please install ffmpeg:")
        print("   Windows: Download from https://ffmpeg.org/download.html")
        print("   Or use: choco install ffmpeg  (if you have Chocolatey)")
        print("   Or use: winget install ffmpeg  (if you have winget)")
        print("\n💡 Make sure ffmpeg is added to your system PATH")
        print("="*60 + "\n")
    except Exception as e:
        print(f"❌ Audio processing error: {e}")
        print(f"   Error type: {type(e).__name__}")
        if "ffmpeg" in str(e).lower():
            print("   💡 This might be an ffmpeg-related issue. Check if ffmpeg is installed correctly.")
    finally:
        if AUDIO_SOURCE_TYPE == "s3_url":
            print("\n📁 Audio file processing completed")
        else:
            print("\n🔴 Stream closed")

# ========== MAIN ==========
def main():
    stream_audio()
    
    if not tipoff_confirmed:
        print("\n" + "="*60)
        if AUDIO_SOURCE_TYPE == "s3_url":
            print(f"⚠️  Audio file processed - No {GAME_EVENT} detected")
        else:
            print(f"⚠️  Stream ended - No {GAME_EVENT} detected")
        print("="*60)

if __name__ == "__main__":
    try:
        main()
    finally:
        # Print log completion message before closing
        print(f"\n📝 Log saved to {LOG_FILE}")
        print(f"📝 Logging ended at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        # Restore stdout and close log file
        sys.stdout = tee.terminal
        tee.close()