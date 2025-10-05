import pygame
import speech_recognition as sr
import pyttsx3
import threading
import time
import queue
from pydub import AudioSegment
import re
import sys
import os

def get_resource_path(relative_path):
    """
    get the absolute path to a resource file
    """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# === CONFIG ===
FONT_PATH = get_resource_path("fonts/DTM-Sans.otf")
FONT_SIZE = 32
AUDIO_DEVICE_NAME = "Toby Fox"
TEXTBOX_WIDTH = 600
TTS_RATE = 120  # slower TTS

custom_words = {"tricky Tony": "Tricky Tony",
                "Toby radiation Fox": "Toby \"Radiation\" Fox",
                "Chris": "Kris",
                "undertale": "Undertale",
                "Delta Rune": "Deltarune", "Delta room": "Deltarune", "Delta Road": "Deltarune", "deltarune": "Deltarune",
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
pygame.mixer.init() # for sounds
flip_sound = pygame.mixer.Sound(get_resource_path("sfx/flip.mp3"))
hurt_sound = pygame.mixer.Sound(get_resource_path("sfx/hurt.mp3"))
heal_sound = pygame.mixer.Sound(get_resource_path("sfx/heal.mp3"))

# load dog images
dog_scale = 5

dog_closed = pygame.image.load(get_resource_path("img/dog_closed.png")).convert_alpha()
dog_closed = pygame.transform.scale(
    dog_closed, (dog_closed.get_width() * dog_scale, dog_closed.get_height() * dog_scale)
)
dog_closed = pygame.transform.flip(dog_closed, True, False)

dog_open = pygame.image.load(get_resource_path("img/dog_open.png")).convert_alpha()
dog_open = pygame.transform.scale(
    dog_open, (dog_open.get_width() * dog_scale, dog_open.get_height() * dog_scale)
)
dog_open = pygame.transform.flip(dog_open, True, False)

dog_walk_1 = pygame.image.load(get_resource_path("img/dog_walk_1.png")).convert_alpha()
dog_walk_1 = pygame.transform.scale(
    dog_walk_1, (dog_walk_1.get_width() * dog_scale, dog_walk_1.get_height() * dog_scale)
)
dog_walk_1 = pygame.transform.flip(dog_walk_1, True, False)

dog_walk_2 = pygame.image.load(get_resource_path("img/dog_walk_2.png")).convert_alpha()
dog_walk_2 = pygame.transform.scale(
    dog_walk_2, (dog_walk_2.get_width() * dog_scale, dog_walk_2.get_height() * dog_scale)
)
dog_walk_2 = pygame.transform.flip(dog_walk_2, True, False)

dog_state = dog_closed
dog_rect = dog_closed.get_rect()
dog_rect.midbottom = (400, 580)

# and poisoned image
poisoned_point = pygame.image.load(get_resource_path("img/poison_point.png")).convert_alpha()
poisoned_point = pygame.transform.scale(
    poisoned_point, (poisoned_point.get_width() * 2, poisoned_point.get_height() * 2)
)
poisoned_rect = poisoned_point.get_rect()
poisoned_rect.midbottom = (600, 540)

# === DOG FLIP ===
dog_flipping = False
flip_start_time = 0
flip_duration = 0.7  # seconds
flip_center_offset = -150  # how big is dog flip

# and other dog stuff (besides dog scale)
poisoned = False
speaking = False
walk_in_timer_time = 2.5 # seconds
walk_in_timer = walk_in_timer_time
walk_start = (-200, 580)
walk_rect = dog_closed.get_rect()
walk_rect.midbottom = walk_start

# === GLOBALS ===
display_words = []
running = True
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
    if text == "":
        display_words = []
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

def tint_surface(surface, tint_color):
    """Return a copy of surface where white pixels are replaced with the tint color (preserves transparency)."""
    tinted = surface.copy()
    arr = pygame.surfarray.pixels3d(tinted)
    alpha = pygame.surfarray.pixels_alpha(tinted)

    # Apply tint only where the pixel is "white-ish"
    white_mask = (arr[:, :, 0] > 200) & (arr[:, :, 1] > 200) & (arr[:, :, 2] > 200)
    arr[white_mask] = tint_color  # Replace white with lime (or whatever color)
    
    # Release the array locks
    del arr
    del alpha

    return tinted

def rotate_image_around_pivot(image, pivot, radius, angle):
    """
    Rotates the image around a pivot point at a given radius and angle.
    """
    # compute rotated image
    rotated_image = pygame.transform.rotate(image, angle + 180)

    # compute offset (center relative to pivot)
    offset = pygame.math.Vector2(0, radius)  # start directly below pivot
    offset.rotate_ip(-angle)  # rotate CCW

    # compute new position for center of image
    new_center = (pivot[0] + offset.x, pivot[1] + offset.y)

    # make rect centered at new position
    rotated_rect = rotated_image.get_rect(center=new_center)
    return rotated_image, rotated_rect

def ease_out_quad(t):
    """for dog walk"""
    return -t * (t - 2)

def draw_text():
    """Draws text and dog oops"""

    global dog_state, dog_flipping, flip_start_time

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
    current_dog = dog_state

    # if poisoned, tint green
    if poisoned:
        current_dog = tint_surface(current_dog, (31, 192, 1))

        # draw poisoned arrow
        screen.blit(poisoned_point, poisoned_rect)

    if dog_flipping:
        # calculate flip progress 0 → 1
        elapsed = time.time() - flip_start_time
        progress = min(elapsed / flip_duration, 1.0)
        angle = 180 + (360 * progress)  # linear CCW rotation

        # pivot point above the dog
        pivot = (dog_rect.centerx, dog_rect.centery + flip_center_offset)
        rotated_image, rot_rect = rotate_image_around_pivot(current_dog, pivot, flip_center_offset, angle)
        screen.blit(rotated_image, rot_rect)

        # stop flip when done
        if progress >= 1.0:
            dog_flipping = False
    elif walk_in_timer > 0:
        walk_progress = -(walk_in_timer / walk_in_timer_time) + 1 # from 0 to 1
        eased_progress = ease_out_quad(walk_progress)

        walk_rect.midbottom = (walk_start[0] + (dog_rect.midbottom[0] - walk_start[0]) * eased_progress, walk_start[1] + (dog_rect.midbottom[1] - walk_start[1]) * eased_progress)
        screen.blit(current_dog, walk_rect)
    else:
        screen.blit(current_dog, dog_rect)

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

# === MAIN LOOP ===
delta_time = 30 # milliseconds
main_stuff_started = False
dog_toggle_time = time.time()
while running:
    current_time = time.time()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    
        elif event.type == pygame.KEYDOWN:
            if walk_in_timer <= 0:
                if event.key == pygame.K_z:
                    if not speaking:
                        # DOG. FLIP.
                        speak_and_display("")
                        flip_sound.play()
                        if not poisoned:
                            dog_flipping = True
                            flip_start_time = time.time()
                elif event.key == pygame.K_x:
                    if not dog_flipping:
                        poisoned = not poisoned

                        if poisoned:
                            hurt_sound.play()
                        else:
                            heal_sound.play()

    if main_stuff_started:
        # animate dog at 5 toggles/sec only while speaking
        if speaking and current_time - dog_toggle_time > 0.1:
            dog_state = dog_open if dog_state == dog_closed else dog_closed
            dog_toggle_time = current_time
        elif not speaking:
            dog_state = dog_closed
    else:
        # same thing but for walking
        if current_time - dog_toggle_time > 0.2:
            dog_state = dog_walk_1 if dog_state == dog_walk_2 else dog_walk_2
            dog_toggle_time = current_time

    draw_text()

    walk_in_timer = max(0, walk_in_timer - delta_time / 1000) # bite me

    if walk_in_timer == 0 and not main_stuff_started:
        # start recognition/TTS loop in separate thread
        threading.Thread(target=main_loop, daemon=True).start()
        threading.Thread(target=tts_worker, daemon=True).start()
        threading.Thread(target=console_input_loop, daemon=True).start()
        main_stuff_started = True
    
    pygame.time.delay(delta_time)

pygame.quit()
