import pygame
import speech_recognition as sr
import pyttsx3
import threading
import time
import queue
from pydub import AudioSegment
import re

# === CONFIG ===
FONT_PATH = "DTM-Sans.otf"
FONT_SIZE = 32
AUDIO_DEVICE_NAME = "Toby Fox"
TEXTBOX_WIDTH = 600
TTS_RATE = 120  # slower TTS

custom_words = {"tricky Tony": "Tricky Tony",
                "Toby radiation Fox": "Toby \"Radiation\" Fox",
                "Chris": "Kris",
                "undertale": "Undertale",
                "Delta Rune": "Deltarune", "Delta room": "Deltarune",
                "Rossi": "Ralsei", "Rosie": "Ralsei",
                "Noel": "Noelle",
                "Burley": "Berdley", "Berkley": "Berdley",
                "frisk": "Frisk",
                "Cara": "Chara",
                "toriel": "Toriel",
                "Sam's": "Sans",
                "undyne": "Undyne",
                "alphys": "Alphys", "Elvis": "Alphys",
                "asgore": "Asgore", "the score": "Asgore",
                "asriel": "Asriel",
                "Lance": "Lancer",
                "Anna": "Tenna", "Hannah": "Tenna",
                "Mr antennas": "Mr. (Ant) Tenna's",
                "Mr antenna": "Mr. (Ant) Tenna",
                "TV time": "TV Time!",
                "the roaring": "the Roaring",
                "the night": "the Knight",
                "the Roaring night": "the Roaring Knight", "The Roaring night": "the Roaring Knight",
                "jackenstein": "Jackenstein", "Jack and Stein": "Jackenstein"}

# === PYGAME ===
pygame.init()
screen = pygame.display.set_mode((800, 600))
pygame.display.set_caption("Toby Fox Simulator")
font = pygame.font.Font(FONT_PATH, FONT_SIZE)

# load dog images
dog_closed = pygame.image.load("dog_closed.png").convert_alpha()
dog_open = pygame.image.load("dog_open.png").convert_alpha()
dog_closed = pygame.transform.scale(
    dog_closed, (dog_closed.get_width() * 5, dog_closed.get_height() * 5)
)
dog_open = pygame.transform.scale(
    dog_open, (dog_open.get_width() * 5, dog_open.get_height() * 5)
)
dog_state = dog_closed
dog_rect = dog_closed.get_rect()
dog_rect.midbottom = (400, 580)

# === GLOBALS ===
display_words = []
running = True
speaking = False # handles dog talking
dog_toggle_time = 0.0
tts_queue = queue.Queue()

r = sr.Recognizer()
r.pause_threshold = 1.5  # seconds of silence to consider end of a phrase (default 0.8)
r.non_speaking_duration = 0  # how long to wait after last sound
r.energy_threshold = 300  # sensitivity to noise (lower = more sensitive)
mic = sr.Microphone()

def process_text(text):
    """Replace some words with custom words that Toby would say"""

    text_lower = text
    for phrase, replacement in sorted(custom_words.items(), key=lambda x: -len(x[0])):
        if phrase in text_lower:
            text_lower = text_lower.replace(phrase, replacement)
    return text_lower

def clean_text_for_tts(text):
    """Remove parenthesis and punctuation so tts doesn't do weird pauses"""

    text = re.sub(r"[()]", "", text)
    text = text.replace(",", "").replace(".", "").replace("?", "").replace("!", "")
    return text

def recognize_speech():
    """Listen to user, process and return their text"""

    with mic as source:
        print("Listening...")
        r.adjust_for_ambient_noise(source, duration=0.5)
        audio = r.listen(source, timeout=None, phrase_time_limit=None)
    
    print("Processing...")

    audio_segment = AudioSegment(
        data=audio.get_wav_data(),
        sample_width=audio.sample_width,
        frame_rate=audio.sample_rate,
        channels=1
    )
    audio_segment += AudioSegment.silent(duration=1000)

    # feed to recognize_google
    audio_with_padding = sr.AudioData(
        audio_segment.raw_data,
        audio.sample_rate,
        audio.sample_width
    )

    try:
        text = r.recognize_google(audio_with_padding)
        print(">>", text)

        processed_text = process_text(text)
        print(">> (", processed_text, ")")
        return processed_text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError as e:
        print("API Error:", e)
        return ""

def speak_and_display(text):
    """speaks text word by word while updating display"""

    global display_words, speaking

    words = text.split()
    display_words = ["*"]
    speaking = True

    engine = pyttsx3.init()
    engine.setProperty("rate", TTS_RATE)

    voices = engine.getProperty("voices")
    for v in voices:
        if AUDIO_DEVICE_NAME.lower() in v.name.lower():
            engine.setProperty("voice", v.id)
            break

    def on_word(name, location, length):
        idx = len(display_words) - 1
        if idx < len(words):
            display_words.append(words[idx])

    engine.connect("started-word", on_word)
    engine.say(clean_text_for_tts(text))
    engine.runAndWait()

    speaking = False

def wrap_text(text, font, width):
    """wrap text in pygame paragraph above dog"""

    words = text.split()
    lines = []
    line = ""
    for w in words:
        test_line = line + (" " if line else "") + w
        if font.size(test_line)[0] <= width:
            line = test_line
        else:
            lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines

def draw_text():
    """draws text and dog oops"""

    screen.fill((0, 0, 0))
    text_str = " ".join(display_words)
    lines = wrap_text(text_str, font, TEXTBOX_WIDTH)

    total_height = len(lines) * font.get_height()
    y = 400 - total_height

    for line in lines:
        text_surface = font.render(line, True, (255, 255, 255))
        rect = text_surface.get_rect()
        rect.midtop = (400, y)
        screen.blit(text_surface, rect)
        y += font.get_height()

    # draw dog
    screen.blit(dog_state, dog_rect)
    pygame.display.flip()

# === continuous recognition/TTS loop ===
def main_loop():
    while running:
        text = recognize_speech()
        if text.strip():
            tts_queue.put(text.strip())

def tts_worker():
    while running:
        try:
            text = tts_queue.get(timeout=0.1)
            speak_and_display(text)
        except queue.Empty:
            continue

def console_input_loop():
    while running:
        try:
            user_text = input()  # blocking call in its own thread
            if user_text.strip():
                tts_queue.put(user_text.strip())
        except EOFError:
            break

# start recognition/TTS loop in separate thread
threading.Thread(target=main_loop, daemon=True).start()
threading.Thread(target=tts_worker, daemon=True).start()
threading.Thread(target=console_input_loop, daemon=True).start()

# === MAIN LOOP ===
dog_toggle_time = time.time()
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # animate dog at 5 toggles/sec only while speaking
    if speaking and time.time() - dog_toggle_time > 0.1:
        dog_state = dog_open if dog_state == dog_closed else dog_closed
        dog_toggle_time = time.time()
    elif not speaking:
        dog_state = dog_closed

    draw_text()
    pygame.time.delay(30)

pygame.quit()
