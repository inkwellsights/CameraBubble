"""
Isolates the 'hold space' from gestures. Run it, then immediately click into
your dictation tool / WezTerm and start talking. It holds SPACE for 4 seconds
exactly like the Open_Palm gesture does, then releases.

If your voice tool records during those 4s -> injection is fine, gesture path is the issue.
If it does NOT record -> your tool ignores injected keys (needs a different trigger).

Run:  python test_hold.py
"""
import time, pyautogui
pyautogui.PAUSE = 0

print("Focus your dictation tool/terminal NOW. Holding SPACE in 3...")
time.sleep(1); print("2..."); time.sleep(1); print("1..."); time.sleep(1)
print(">>> SPACE DOWN  (recording should start - talk now)")
pyautogui.keyDown('space')
time.sleep(4)
pyautogui.keyUp('space')
print(">>> SPACE UP  (recording should stop / transcribe)")
print("Did it record? If yes -> injection works. If no -> tool ignores injected keys.")
