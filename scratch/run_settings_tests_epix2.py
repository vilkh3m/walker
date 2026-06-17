import xml.etree.ElementTree as ET
import subprocess
import time
import os
import glob
import sys
from PIL import Image

PROPERTIES_PATH = "/Users/wwarby/GIT/walker/resources/properties.xml"
WALKER_VIEW_PATH = "/Users/wwarby/GIT/walker/source/WalkerView.mc"
SDK_BIN_PATH = "/Users/wwarby/Library/Application Support/Garmin/ConnectIQ/Sdks/connectiq-sdk-mac-9.2.0-2026-06-09-92a1605b2/bin"
JAVA_PATH = "/opt/homebrew/opt/openjdk@17/bin"
DEV_KEY = "/Users/wwarby/ConnectIQ/developer_key.der"
ARTIFACTS_DIR = "/Users/wwarby/.gemini/antigravity/brain/f8f3e32a-aff8-4b9a-8f42-3f3b98a29ca4"

# Backup original files to restore later
with open(PROPERTIES_PATH, "r") as f:
    ORIGINAL_PROPERTIES = f.read()

with open(WALKER_VIEW_PATH, "r") as f:
    ORIGINAL_SOURCE = f.read()

def instrument_source():
    target = "\t\tcalories = info.calories;\n\t\tdayCalories = activityMonitorInfo.calories;"
    
    diagnostic_print = """
\t\tSystem.print("DIAGNOSTIC: ");
\t\tSystem.print("d="); System.print(darkModeFromSetting);
\t\tSystem.print(", s="); System.print(showSpeedInsteadOfPace);
\t\tSystem.print(", pm="); System.print(paceOrSpeedMode);
\t\tSystem.print(", hm="); System.print(heartRateMode);
\t\tSystem.print(", z="); System.print(showHeartRateZone);
\t\tSystem.print(", hr="); System.print(heartRate != null ? heartRate : "null");
\t\tSystem.print(", hrZone="); System.print(heartRateZone != null ? heartRateZone : "null");
\t\tSystem.print(", val="); System.print(paceOrSpeed != null ? paceOrSpeed : "null");
\t\tSystem.print(", rawHr="); System.print(info.currentHeartRate != null ? info.currentHeartRate : "null");
\t\tSystem.print(", rawSpeed="); System.print(info.currentSpeed != null ? info.currentSpeed : "null");
\t\tSystem.print(", paceFactor="); System.print(kmOrMileInKmPace);
\t\tSystem.print(", steps="); System.print(steps != null ? steps : 0);
\t\tSystem.print(", daySteps="); System.print(daySteps != null ? daySteps : 0);
\t\tSystem.print(", calories="); System.print(calories != null ? calories : 0);
\t\tSystem.print(", dayCalories="); System.print(dayCalories != null ? dayCalories : 0);
\t\tSystem.print(", timerActive="); System.print(timerActive);
\t\tSystem.print(", stepsWhenTimerBecameActive="); System.print(stepsWhenTimerBecameActive);
\t\tSystem.print(", time="); System.println(time != null ? time : "null");"""
    
    replacement = target + diagnostic_print
    
    if target in ORIGINAL_SOURCE:
        with open(WALKER_VIEW_PATH, "w") as f:
            f.write(ORIGINAL_SOURCE.replace(target, replacement))
        print("WalkerView.mc instrumented successfully.")
    else:
        print("Error: Could not find target integration point in WalkerView.mc!")
        sys.exit(1)

def restore_source():
    with open(WALKER_VIEW_PATH, "w") as f:
        f.write(ORIGINAL_SOURCE)
    print("WalkerView.mc restored to original state.")

def update_property(prop_id, value):
    tree = ET.parse(PROPERTIES_PATH)
    root = tree.getroot()
    properties_tag = root.find("properties")
    for prop in properties_tag.findall("property"):
        if prop.attrib.get("id") == prop_id:
            prop.text = str(value).lower() if isinstance(value, bool) else str(value)
            break
    tree.write(PROPERTIES_PATH)

def run_cmd(cmd_list):
    env = os.environ.copy()
    env["PATH"] = f"{SDK_BIN_PATH}:{JAVA_PATH}:{env.get('PATH', '')}"
    res = subprocess.run(cmd_list, env=env, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Command failed: {' '.join(cmd_list)}")
        print(f"Stderr: {res.stderr}")
    return res

def run_cmd_async(cmd_list):
    env = os.environ.copy()
    env["PATH"] = f"{SDK_BIN_PATH}:{JAVA_PATH}:{env.get('PATH', '')}"
    proc = subprocess.Popen(cmd_list, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
    return proc

def run_applescript(script):
    process = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    if process.returncode != 0:
        print(f"AppleScript Error: {process.stderr}")
    return process.stdout.strip()

def get_window_coords():
    res = run_applescript('''
        tell application "System Events" to tell process "simulator"
            set winList to every window
            repeat with win in winList
                try
                    set t to name of win
                    if t is not missing value and t contains "CIQ Simulator" then
                        set pos to position of win
                        set sz to size of win
                        return (item 1 of pos) as string & "," & (item 2 of pos) as string & "," & (item 1 of sz) as string & "," & (item 2 of sz) as string
                    end if
                end try
            end repeat
        end tell
    ''')
    try:
        parts = [int(x.strip()) for x in res.split(",")]
        if len(parts) == 4:
            return parts
    except Exception as e:
        print(f"Error parsing window coords: {e} (raw output: '{res}')")
    return None

def clear_cached_settings():
    set_files = glob.glob("/var/folders/c_/xmgn_r492sqcjlh29mf2tdx40000gn/T/com.garmin.connectiq/GARMIN/APPS/SETTINGS/*.SET")
    for f in set_files:
        try:
            os.remove(f)
            print(f"Cleared cached settings file: {f}")
        except Exception as e:
            print(f"Failed to clear {f}: {e}")

def kill_app_in_simulator():
    run_applescript('''
        tell application "System Events" to tell process "simulator"
            set frontmost to true
            if exists menu item "Kill App" of menu 1 of menu bar item "File" of menu bar 1 then
                click menu item "Kill App" of menu 1 of menu bar item "File" of menu bar 1
            end if
        end tell
    ''')

def ensure_simulation_playing():
    print("Ensuring telemetry simulation is active and playing...")
    for attempt in range(3):
        # Open Activity Data dialog if not open
        run_applescript('''
            tell application "System Events" to tell process "simulator"
                set frontmost to true
                if not (exists window 1 whose title is "") then
                    click menu item "Activity Data" of menu 1 of menu bar item "Simulation" of menu bar 1
                    delay 1.5
                end if
            end tell
        ''')
        
        # Read time, wait 1.5s, read time again
        time_str1 = run_applescript('''
            tell application "System Events" to tell process "simulator"
                tell window 1 whose title is ""
                    set all_texts to value of every static text
                    repeat with txt in all_texts
                        if txt contains ":" and length of (txt as string) is 8 then
                            return (txt as string)
                        end if
                    end repeat
                end tell
            end tell
        ''')
        time.sleep(1.5)
        time_str2 = run_applescript('''
            tell application "System Events" to tell process "simulator"
                tell window 1 whose title is ""
                    set all_texts to value of every static text
                    repeat with txt in all_texts
                        if txt contains ":" and length of (txt as string) is 8 then
                            return (txt as string)
                        end if
                    end repeat
                end tell
            end tell
        ''')
        
        print(f"Simulation time check (attempt {attempt+1}): '{time_str1}' -> '{time_str2}'")
        if time_str1 != time_str2 and time_str1 != "" and time_str2 != "":
            print("Telemetry simulation is running.")
            return True
            
        print("Telemetry simulation is paused/stopped. Clicking play button (button 11)...")
        run_applescript('''
            tell application "System Events" to tell process "simulator"
                tell window 1 whose title is ""
                    click button 11
                end tell
            end tell
        ''')
        time.sleep(1.0)
        
    print("Warning: Could not verify telemetry simulation is running.")
    return False


def setup_activity_monitor_info(steps_per_minute=120, step_goal=5000):
    print(f"Configuring Activity Monitor: Steps/Min={steps_per_minute}, Goal={step_goal}")
    run_applescript(f'''
        tell application "System Events" to tell process "simulator"
            set frontmost to true
            
            -- Open dialog
            click menu item "Set Activity Monitor Info" of menu 1 of menu item "Activity Monitoring" of menu 1 of menu bar item "Simulation" of menu bar 1
            delay 1.0
            
            set win to window "Edit Activity Monitor Info"
            
            -- Focus first text field
            set focused of text field 1 of win to true
            delay 0.3
            
            -- Shift+Tab goes to Today -> Steps Per Minute
            key code 48 using shift down
            delay 0.1
            
            keystroke "a" using command down
            delay 0.1
            keystroke "{steps_per_minute}"
            delay 0.2
            
            -- Tab to Step Goal
            keystroke tab
            delay 0.1
            keystroke "a" using command down
            delay 0.1
            keystroke "{step_goal}"
            delay 0.2
            
            keystroke return
            delay 0.3
            click button "Apply" of win
            delay 0.3
            
            -- Close window by sending Escape
            key code 53
            delay 0.5
        end tell
    ''')

def fast_forward_simulation(minutes=25):
    print(f"Fast forwarding activity tracking by {minutes} minutes...")
    run_applescript(f'''
        tell application "System Events" to tell process "simulator"
            set frontmost to true
            click menu item "Fast Forward" of menu 1 of menu item "Activity Monitoring" of menu 1 of menu bar item "Simulation" of menu bar 1
            delay 1.0
            tell window "Fast Forward Activity Tracking"
                set focused of text field 1 to true
                delay 0.3
            end tell
            keystroke "a" using command down
            delay 0.1
            keystroke "{minutes}"
            delay 0.3
            keystroke return
        end tell
    ''')
    time.sleep(2)

def verify_screenshot_darkness(filepath, expected_dark):
    if not os.path.exists(filepath):
        print(f"Error: Screenshot file {filepath} does not exist.")
        return False
    
    img = Image.open(filepath)
    w, h = img.size
    
    cx = w // 2
    cy = h // 2 + 20
    sample_box = (cx - 80, cy - 80, cx - 60, cy - 60)
    cropped = img.crop(sample_box)
    pixels = list(cropped.getdata())
    avg_brightness = sum(sum(p[:3])/3.0 for p in pixels) / len(pixels)
    
    print(f"Screenshot {os.path.basename(filepath)} sample brightness: {avg_brightness:.2f}")
    if expected_dark:
        if avg_brightness > 50:
            print(f"FAILED: Expected dark background (brightness < 50), got {avg_brightness:.2f}")
            return False
    else:
        if avg_brightness < 200:
            print(f"FAILED: Expected light background (brightness > 200), got {avg_brightness:.2f}")
            return False
            
    print("SUCCESS: Visual background color verified.")
    return True

class NonBlockingLineReader:
    def __init__(self, stream):
        self.stream = stream.raw if hasattr(stream, "raw") else stream
        self.buffer = b""
        
        # Make the raw file descriptor non-blocking
        import fcntl
        import os
        fd = self.stream.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        
    def read_line(self):
        # Read whatever raw bytes are available
        try:
            chunk = self.stream.read(1024)
            if chunk is not None:
                if len(chunk) == 0:
                    # EOF
                    if self.buffer:
                        line = self.buffer
                        self.buffer = b""
                        return line.decode('utf-8', errors='ignore').strip()
                    return None # Truly EOF
                self.buffer += chunk
        except BlockingIOError:
            pass
            
        # Extract a line if we have a newline
        if b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            return line.decode('utf-8', errors='ignore').strip()
            
        return "" # No full line available yet

def drain_pipe(reader):
    count = 0
    while True:
        line = reader.read_line()
        if line is None or line == "":
            break
        print(f"DRAINED: {line}")
        count += 1
    print(f"Drained {count} stale lines from stream.")

def run_and_verify_diagnostics(proc, expected_settings, duration=15, hr_history=None, speed_history=None, stdout_reader=None, stderr_reader=None):
    start_time = time.time()
    verified = False
    diagnostic_count = 0
    timer_active_count = 0
    
    # Always start with clean real-time history to avoid fast-forward desync
    hr_history = []
    speed_history = []
    
    steps_history = []
    day_steps_history = []
    calories_history = []
    day_calories_history = []
    
    print(f"Monitoring diagnostics for {duration} seconds...")
    while time.time() - start_time < duration:
        # Read stdout
        while True:
            line_str = stdout_reader.read_line()
            if line_str is None or line_str == "":
                break
            
            print(f"Console: {line_str}")
            if "DIAGNOSTIC:" in line_str:
                try:
                    parts = line_str.replace("DIAGNOSTIC:", "").strip().split(", ")
                    diag = {}
                    for part in parts:
                        if "=" in part:
                            k, v = part.split("=", 1)
                            diag[k.strip()] = v.strip()
                    
                    # Assert settings match
                    assert diag["d"] == str(expected_settings["d"]).lower()
                    assert diag["s"] == str(expected_settings["s"]).lower()
                    assert int(diag["pm"]) == expected_settings["pm"]
                    assert int(diag["hm"]) == expected_settings["hm"]
                    assert diag["z"] == str(expected_settings["z"]).lower()
                    
                    # Parse telemetry values
                    raw_hr = None if diag["rawHr"] == "null" else int(diag["rawHr"])
                    raw_speed = None if diag["rawSpeed"] == "null" else float(diag["rawSpeed"])
                    hr = None if diag["hr"] == "null" else float(diag["hr"])
                    val = None if diag["val"] == "null" else float(diag["val"])
                    hr_zone = None if diag["hrZone"] == "null" else diag["hrZone"]
                    pace_factor = float(diag["paceFactor"])
                    
                    # Parse steps/calories values
                    steps = int(diag["steps"])
                    day_steps = int(diag["daySteps"])
                    calories = int(diag["calories"])
                    day_calories = int(diag["dayCalories"])
                    
                    if diag["timerActive"] == "true":
                        timer_active_count += 1
                        
                        if raw_hr is not None:
                            hr_history.append(raw_hr)
                        if raw_speed is not None:
                            speed_history.append(raw_speed)
                        
                        steps_history.append(steps)
                        day_steps_history.append(day_steps)
                        calories_history.append(calories)
                        day_calories_history.append(day_calories)
                    
                    # Assert 1: Steps & Calories start at high levels (due to fast forwarding)
                    assert day_steps >= 3000, f"Expected daySteps >= 3000, got {day_steps}"
                    
                    # Assert 2: Pace vs Speed math
                    if raw_speed is not None and raw_speed > 0.1 and val is not None:
                        if expected_settings["s"]:
                            if expected_settings["pm"] == 0:
                                                    expected_val = (raw_speed / pace_factor) * 3.6
                                                    assert abs(val - expected_val) < 0.1, f"Speed calculation wrong: got {val}, expected {expected_val}"
                        else:
                            if expected_settings["pm"] == 0:
                                                    expected_val = (pace_factor / raw_speed) * 1000000.0
                                                    assert abs(val - expected_val) < 1.0, f"Pace calculation wrong: got {val}, expected {expected_val}"
                    
                    # Assert 3: HR Zone display
                    if expected_settings["z"]:
                        if raw_hr is not None and hr is not None:
                            assert hr_zone is not None
                            assert hr_zone in ["1", "2", "3", "4", "5", "-", "+"]
                    else:
                        assert hr_zone is None
                    
                    # Assert 4: HR Averaging smoothing
                    if expected_settings["hm"] > 0 and timer_active_count >= expected_settings["hm"] and len(hr_history) >= expected_settings["hm"] and hr is not None:
                        window_size = expected_settings["hm"]
                        recent_history = hr_history[-window_size:]
                        expected_avg = sum(recent_history) / len(recent_history)
                        assert abs(hr - expected_avg) < 1.0, f"HR Average smoothing mismatch: expected {expected_avg}, got {hr}"
                        if len(set(recent_history)) > 1:
                            assert hr != raw_hr
                    
                    # Assert 5: Pace Averaging smoothing
                    if expected_settings["pm"] > 0 and timer_active_count >= expected_settings["pm"] and len(speed_history) >= expected_settings["pm"] and val is not None and raw_speed is not None:
                        window_size = expected_settings["pm"]
                        recent_history = speed_history[-window_size:]
                        expected_avg_speed = sum(recent_history) / len(recent_history)
                        if expected_avg_speed > 0.1:
                            if expected_settings["s"]:
                                                    expected_val = (expected_avg_speed / pace_factor) * 3.6
                                                    assert abs(val - expected_val) < 0.1
                            else:
                                                    expected_val = (pace_factor / expected_avg_speed) * 1000000.0
                                                    assert abs(val - expected_val) < 1.0
                    
                    diagnostic_count += 1
                    if diagnostic_count >= 5:
                        verified = True
                except AssertionError as e:
                    print(f"ASSERTION FAILED: {e}")
                    return False
                
        # Read stderr
        while True:
            line_str = stderr_reader.read_line()
            if line_str is None or line_str == "":
                break
            print(f"STDERR: {line_str}")
                
        time.sleep(0.05)
        
    if not verified:
        print("Verification failed: Did not receive enough telemetry logs to verify functionality.")
        return False
        
    # Assert 6: Steps and Calories actually incremented during the active timer workout
    if len(steps_history) > 1:
        assert steps_history[-1] > steps_history[0], f"Workout steps did not increment: {steps_history[0]} -> {steps_history[-1]}"
        assert day_steps_history[-1] > day_steps_history[0], f"Daily steps did not increment: {day_steps_history[0]} -> {day_steps_history[-1]}"
        assert calories_history[-1] > calories_history[0], f"Workout calories did not increment: {calories_history[0]} -> {calories_history[-1]}"
        assert day_calories_history[-1] > day_calories_history[0], f"Daily calories did not increment: {day_calories_history[0]} -> {day_calories_history[-1]}"
        print(f"Verified Increments: Steps incremented by {steps_history[-1] - steps_history[0]} during workout.")
        print(f"Verified Increments: Calories incremented by {calories_history[-1] - calories_history[0]} during workout.")
    else:
        print("Warning: Not enough workout steps samples collected to verify increments.")
        
    print("SUCCESS: Diagnostics functional verification passed!")
    return True


def ensure_simulator_running(force=False):
    if not force:
        # Check if simulator process and window are already present
        pg = subprocess.run(["pgrep", "-f", "ConnectIQ.app/Contents/MacOS/simulator"], capture_output=True)
        if pg.returncode == 0:
            window_names = run_applescript('tell application "System Events" to tell process "simulator" to get name of every window')
            if "CIQ Simulator" in window_names:
                print("Simulator is already running and ready.")
                return
                
    print("Force-restarting simulator to ensure clean state and responsiveness...")
    subprocess.run(["killall", "simulator"], capture_output=True)
    subprocess.run(["pkill", "-f", "ConnectIQ"], capture_output=True)
    time.sleep(1.0)
    subprocess.run(["open", "-a", "/Users/wwarby/Library/Application Support/Garmin/ConnectIQ/Sdks/connectiq-sdk-mac-9.2.0-2026-06-09-92a1605b2/bin/ConnectIQ.app"])
    time.sleep(5.0)
    for _ in range(15):
        try:
            # Check process running first
            pg = subprocess.run(["pgrep", "-f", "ConnectIQ.app/Contents/MacOS/simulator"], capture_output=True)
            if pg.returncode == 0:
                window_names = run_applescript('tell application "System Events" to tell process "simulator" to get name of every window')
                if "CIQ Simulator" in window_names:
                    print("Simulator window found. Waiting 10 seconds for device boot...")
                    time.sleep(10.0)
                    print("Simulator is ready.")
                    break
        except Exception as e:
            print(f"Waiting for simulator window... ({e})")
        time.sleep(1)

def test_settings(name, pm, hm, z, s, d):
    print(f"\n--- Testing Configuration: {name} ---")
    ensure_simulator_running(force=True)
    
    speed_history = []
    hr_history = []
    
    # Kill any active app running in the simulator
    kill_app_in_simulator()
    time.sleep(2)
    
    update_property("pm", pm)
    update_property("hm", hm)
    update_property("z", z)
    update_property("s", s)
    update_property("d", d)
    
    clear_cached_settings()

    print("Compiling Walker app for epix2...")
    run_cmd(["monkeyc", "-f", "/Users/wwarby/GIT/walker/monkey.jungle", "-y", DEV_KEY, "-o", "/Users/wwarby/GIT/walker/bin/walker-epix2.prg", "-d", "epix2"])
    
    try:
        subprocess.run(["cp", "/Users/wwarby/GIT/walker/bin/walker-epix2-settings.json", "/Users/wwarby/GIT/walker/bin/walker-epix2.json"])
    except:
        pass

    print("Deploying to epix2 simulator asynchronously...")
    proc = run_cmd_async([
        "monkeydo", 
        "/Users/wwarby/GIT/walker/bin/walker-epix2.prg", 
        "epix2", 
        "-a", 
        "/Users/wwarby/GIT/walker/bin/walker-epix2-settings.json:GARMIN/Settings/walker-epix2-settings.json"
    ])
    
    stdout_reader = NonBlockingLineReader(proc.stdout)
    stderr_reader = NonBlockingLineReader(proc.stderr)
    
    time.sleep(8)
    
    # Set default simulator background to White (only applies when app is running)
    print("Setting simulator background color to White...")
    run_applescript('''
        tell application "System Events" to tell process "simulator"
            set frontmost to true
            try
                click menu item "White" of menu 1 of menu item "Background Color" of menu 1 of menu bar item "Data Fields" of menu bar 1
            end try
        end tell
    ''')
    time.sleep(0.5)
    
    # 1. Ensure telemetry data simulation is active and playing
    ensure_simulation_playing()
    
    # 2. Setup Activity Monitor Info dialog (Steps Per Minute = 120, Step Goal = 5000)
    setup_activity_monitor_info(steps_per_minute=120, step_goal=5000)
    
    # 3. Fast forward activity tracking by 25 minutes to generate 3000 steps so far today (120 steps/min * 25 mins = 3000 steps)
    fast_forward_simulation(minutes=25)
    time.sleep(3.0) # Wait for simulator to settle
    
    # 4. Start Workout Recording
    print("Ensuring workout timer is running...")
    drain_pipe(stdout_reader)
    drain_pipe(stderr_reader)
    run_applescript('''
        tell application "System Events" to tell process "simulator"
            set frontmost to true
            -- Open Activity Data dialog if not open
            if not (exists window 1 whose title is "") then
                click menu item "Activity Data" of menu 1 of menu bar item "Simulation" of menu bar 1
                delay 1.5
            end if
            tell window 1 whose title is ""
                -- Ensure telemetry simulation is playing
                set all_texts to value of every static text
                set time_str to ""
                repeat with txt in all_texts
                    if txt contains ":" then
                        set time_str to txt
                        exit repeat
                    end if
                end repeat
                
                delay 1.0
                
                set all_texts2 to value of every static text
                set time_str2 to ""
                repeat with txt in all_texts2
                    if txt contains ":" then
                        set time_str2 to txt
                        exit repeat
                    end if
                end repeat
                
                if time_str is equal to time_str2 then
                    -- Timer is paused, click play (button 11)
                    click button 11
                    delay 1.0
                end if
                
                -- Click the Stop/Start button once to start the activity timer
                click button 3
                delay 1.5
            end tell
        end tell
    ''')
    
    expected_settings = {"pm": pm, "hm": hm, "z": z, "s": s, "d": d}
    duration = 80 if hm == 60 else 25
    verified = run_and_verify_diagnostics(proc, expected_settings, duration=duration, hr_history=hr_history, speed_history=speed_history, stdout_reader=stdout_reader, stderr_reader=stderr_reader)
    
    # Close Activity Data window to expose the watch face
    print("Closing Activity Data window before screenshot...")
    run_applescript('''
        tell application "System Events" to tell process "simulator"
            set frontmost to true
            if exists window 1 whose title is "" then
                tell window 1 whose title is ""
                    click button 12
                end tell
            end if
        end tell
    ''')
    time.sleep(0.5)

    # Find window coordinates to crop simulator window screenshot
    coords = get_window_coords()
    screenshot_path = os.path.join(ARTIFACTS_DIR, f"settings_{name}.png")
    if coords:
        x, y, w, h = coords
        print(f"Capturing watch window only: {w}x{h} at ({x}, {y})")
        subprocess.run(["screencapture", "-R", f"{x},{y},{w},{h}", screenshot_path])
    else:
        subprocess.run(["screencapture", "-x", screenshot_path])
        
    print(f"Captured screenshot to: settings_{name}.png")
    
    screenshot_verified = verify_screenshot_darkness(screenshot_path, expected_dark=d)
    
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        
    if not (verified and screenshot_verified):
        print(f"TEST '{name}' FAILED FUNCTIONAL VERIFICATION!")
        sys.exit(1)

def main():
    instrument_source()
    ensure_simulator_running(force=True)
    try:
        # Test Case 1: Defaults (baseline - White background, 5s Pace Average, HR instant)
        test_settings("defaults", pm=5, hm=0, z=False, s=False, d=False)
        
        # Test Case 2: Dark Mode (Black background)
        test_settings("dark_mode", pm=5, hm=0, z=False, s=False, d=True)
        
        # Test Case 3: HR Zone Display & 60s HR Avg (renders colored heart zones, 60s HR)
        test_settings("hr_zone_60s_avg", pm=5, hm=60, z=True, s=False, d=False)
        
        # Test Case 4: Speed Display & Instant Pace (Speed in km/h or mph instead of pace)
        test_settings("speed_display", pm=0, hm=0, z=False, s=True, d=False)
        
        print("\nAll settings exercised and verified successfully!")
    finally:
        # Restore source file and properties
        restore_source()
        with open(PROPERTIES_PATH, "w") as f:
            f.write(ORIGINAL_PROPERTIES)
        print("Restored original properties.xml file.")

if __name__ == "__main__":
    main()
