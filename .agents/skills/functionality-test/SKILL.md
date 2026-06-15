---
name: functionality-test
description: Executable walkthrough to test all features of the Walker data field in the Garmin Connect IQ simulator.
---

# Walker Functionality Test Plan

## 1. Setup
Deploy Walker on the target device in the simulator:
```bash
PATH="/Users/wwarby/Library/Application Support/Garmin/ConnectIQ/Sdks/connectiq-sdk-mac-9.2.0-2026-06-09-92a1605b2/bin:/opt/homebrew/opt/openjdk@17/bin:$PATH" monkeydo bin/walker-fenix5.prg fenix5
```

---

## 2. Background Color Test
Toggle white vs black background:
```applescript
tell application "System Events" to tell process "simulator"
    -- Open File -> Edit Persistent Storage -> Edit Application.Properties data
    click menu item "Edit Application.Properties data" of menu 1 of menu item "Edit Persistent Storage" of menu 1 of menu bar item "File" of menu bar 1
    -- Toggle background property checkbox and save
end tell
```

---

## 3. Battery Status Rendering Test
Verify battery level percentage and icon coloring:
1. Open Battery Status dialog:
```applescript
tell application "System Events" to tell process "simulator"
    click menu item "Set Battery Status" of menu 1 of menu bar item "Settings" of menu bar 1
end tell
```
2. Set values to:
   - `95%` (Green battery icon, black/white text)
   - `15%` (Yellow battery icon, black text)
   - `5%` (Red battery icon, red/white text)

---

## 4. Heart Rate and Zone Coloring Test
Verify heart rate rendering and color-coded zones:
1. Open Sensor Manager:
```applescript
tell application "System Events" to tell process "simulator"
    click menu item "Manage Sensors" of menu 1 of menu bar item "Settings" of menu bar 1
end tell
```
2. Simulate heart rates:
   - `70 bpm` (Zone 1 - Grey / Blue)
   - `120 bpm` (Zone 2 - Green)
   - `145 bpm` (Zone 3 - Orange)
   - `175 bpm` (Zone 4 - Red)

---

## 5. Daily Steps & Progress Bar Test
Verify daily steps rendering and goal progress bar updates:
1. Open Activity Monitor Info:
```applescript
tell application "System Events" to tell process "simulator"
    click menu item "Set Activity Monitor Info" of menu 1 of menu item "Activity Monitoring" of menu 1 of menu bar item "Simulation" of menu bar 1
end tell
```
2. Set steps:
   - `2500` steps with `5000` goal (50% progress bar)
   - `5000` steps with `5000` goal (100% full progress bar)

---

## 6. FIT Contributor Test
Verify distance, calories, activity steps, and pace calculation during simulated workout:
1. Open Activity Data simulator:
```applescript
tell application "System Events" to tell process "simulator"
    click menu item "Activity Data" of menu 1 of menu bar item "Simulation" of menu bar 1
end tell
```
2. Click "Start" on simulated workout.
3. Fast-forward steps or play simulated telemetry.
4. Stop activity and check FIT file summary outputs.
