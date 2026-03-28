# 🎨 UI/UX Wireframes

**Version:** 1.0 | **Date:** March 2026 | **Author:** Jamiel J.

---

## 1. Design Philosophy

DNA is voice-first. You are 2 meters from the screen. The UI only needs to answer three questions:

- Am I being heard?
- What did DNA say?
- Did it succeed?

**Two components only:** system tray icon + toast notification. No window. No dashboard. No focus required.

---

## 2. System Tray Icon

### Purpose

Always visible in Windows taskbar tray (bottom-right). Shows DNA's current state at a glance. Right-click opens a minimal context menu.

### Icon States

| State | Color | Meaning |
| --- | --- | --- |
| Idle / Listening for wake word | Grey #888888 | Running, waiting for 'Hey DNA' |
| Activated / Recording | Green #27AE60 | Wake word detected, recording |
| Processing / Thinking | Yellow #F39C12 pulsing | STT done, LLM/tool executing |
| Success | Blue #3498DB brief flash | Command completed |
| Error | Red #E74C3C brief flash | Something failed |
| Paused / Muted | Dark grey #333333 | DNA manually paused |

### Tray Position

```
[ Windows Taskbar — Bottom Right Corner ]
┌─────────────────────────────────────────────────────┐
│  ...  [other icons]  [● DNA]  [clock]  [⊞]  │
└─────────────────────────────────────────────────────┘
```

Icon: filled circle, 16x16px, color changes per state table. No text label.

### Right-Click Context Menu

```
┌──────────────────────┐
│  DNA Assistant        │
│  ─────────────────   │
│  ● Status: Listening  │
│  ─────────────────   │
│  ⏸ Pause DNA          │
│  🔄 Restart            │
│  📋 View Command Log   │
│  ✕ Exit               │
└──────────────────────┘
```

| Menu Item | Action |
| --- | --- |
| Pause DNA | Stop wake word listener, icon turns dark grey |
| Restart | Kill and restart dna_[main.py](http://main.py) |
| View Command Log | Open dna_memory.db log viewer |
| Exit | Gracefully terminate all threads |

### Implementation

```
pip install pystray Pillow
```

Create icon image programmatically using Pillow (filled circle). pystray manages Windows tray entry. Swap image on state change.

---

## 3. Toast Notification

### Purpose

Appears bottom-right when DNA speaks a response. Shows the text of what DNA said. Auto-dismisses after 4 seconds. Font large enough to read at 2 meters.

### Toast Wireframe

```
┌────────────────────────────────────────────┐
│  🎙 DNA                            [×]       │
│  ──────────────────────────────────────────  │
│                                              │
│  Opened sales_q1.xlsx. 500 rows,            │
│  8 columns. Chart saved to Desktop.         │
│                                              │
│  ▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░  (4s timer bar)       │
└────────────────────────────────────────────┘
```

### Toast Specifications

| Property | Value |
| --- | --- |
| Position | Bottom-right, 20px from edge |
| Width | 380px fixed |
| Font size | 14pt minimum (readable at 2m) |
| Background | Dark #1A1A2E with white text |
| Auto-dismiss | 4 seconds with progress bar |
| Manual dismiss | Click [x] button |
| Max lines | 4 lines, truncated with '...' |
| Implementation | win10toast or plyer library |

### Toast Variants

| Type | Border Color | Icon | When Used |
| --- | --- | --- | --- |
| Success | Green #27AE60 | ✓ | Command completed |
| Info | Blue #3498DB | ⓘ | Proactive alert |
| Error | Red #E74C3C | ! | Command failed |
| Listening | Yellow #F39C12 | 🎙 | Wake word triggered |

### Implementation

```
pip install plyer
```

---

## 4. Interaction Flow

### Successful Command

| Step | Tray Icon | Toast | Audio |
| --- | --- | --- | --- |
| Idle | Grey | None | None |
| Wake word detected | Green | 'Listening...' (1s) | Optional ping |
| Recording | Green pulsing | None | None |
| Processing | Yellow pulsing | None | None |
| Response ready | Blue flash → Grey | Response text (4s) | Piper TTS speaks |

### Failed Command

| Step | Tray Icon | Toast | Audio |
| --- | --- | --- | --- |
| Processing | Yellow pulsing | None | None |
| Tool fails | Red flash → Grey | Error message (6s, no auto-dismiss) | DNA speaks error |

### Proactive Alert

| Trigger | Tray Icon | Toast | Audio |
| --- | --- | --- | --- |
| CPU >90% | Orange pulse | Warning (8s) | DNA speaks alert |
| New download | Blue pulse | Filename (6s) | DNA speaks filename |

---

## 5. Future GUI (Optional, Post-v2)

If a GUI is ever added — minimal floating panel only, not a dashboard:

```
┌────────────────────────────────┐
│  DNA  [●]  Listening           │
│  ────────────────────────────── │
│  > Hey DNA open Chrome         │
│  ✓ Opened Chrome               │
│  > Volume 60                   │
│  ✓ Volume set to 60            │
└────────────────────────────────┘
```

220x300px floating panel, always-on-top, draggable, last 5 command-response pairs. Toggled via tray menu. Not a priority for v1 or v2.
