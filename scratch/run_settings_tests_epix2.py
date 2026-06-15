import xml.etree.ElementTree as ET
import subprocess
import time
import os
import glob

PROPERTIES_PATH = "/Users/wwarby/GIT/walker/resources/properties.xml"
SDK_BIN_PATH = "/Users/wwarby/Library/Application Support/Garmin/ConnectIQ/Sdks/connectiq-sdk-mac-9.2.0-2026-06-09-92a1605b2/bin"
JAVA_PATH = "/opt/homebrew/opt/openjdk@17/bin"
DEV_KEY = "/Users/wwarby/ConnectIQ/developer_key.der"
ARTIFACTS_DIR = "/Users/wwarby/.gemini/antigravity/brain/f8f3e32a-aff8-4b9a-8f42-3f3b98a29ca4"

# Original contents to restore later
with open(PROPERTIES_PATH, "r") as f:
    ORIGINAL_PROPERTIES = f.read()

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
    # Start asynchronously
    proc = subprocess.Popen(cmd_list, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc

def run_applescript(script):
    process = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
    if process.returncode != 0:
        print(f"AppleScript Error: {process.stderr}")
    return process.stdout.strip()

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

def test_settings(name, pm, hm, z, s, d):
    print(f"\n--- Testing Configuration: {name} ---")
    
    # Kill any active app running in the simulator
    kill_app_in_simulator()
    time.sleep(1)
    
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
    
    time.sleep(4)
    
    print("Ensuring workout timer is running...")
    run_applescript('''
        tell application "System Events" to tell process "simulator"
            if exists window 2 then
                if exists (button "Start" of window 2) then
                    click button "Start" of window 2
                end if
            end if
        end tell
    ''')
    
    time.sleep(4)
    
    screenshot_path = os.path.join(ARTIFACTS_DIR, f"settings_{name}.png")
    subprocess.run(["screencapture", "-x", screenshot_path])
    print(f"Captured screenshot to: settings_{name}.png")
    
    # Clean up the Popen process
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()

def main():
    try:
        # Test Case 1: Defaults (baseline - White background, Pace Mode, HR instant)
        test_settings("defaults", pm=5, hm=0, z=False, s=False, d=False)
        
        # Test Case 2: Dark Mode (Black background)
        test_settings("dark_mode", pm=5, hm=0, z=False, s=False, d=True)
        
        # Test Case 3: HR Zone Display & 60s HR Avg (renders colored heart zones, 60s HR)
        test_settings("hr_zone_60s_avg", pm=5, hm=60, z=True, s=False, d=False)
        
        # Test Case 4: Speed Display & Instant Pace (Speed in km/h or mph instead of pace)
        test_settings("speed_display", pm=0, hm=0, z=False, s=True, d=False)
        
        print("\nAll settings exercised successfully.")
    finally:
        # Restore properties.xml
        with open(PROPERTIES_PATH, "w") as f:
            f.write(ORIGINAL_PROPERTIES)
        print("Restored original properties.xml file.")

if __name__ == "__main__":
    main()
