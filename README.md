# தட்டான் (Thattan)

A Tamil99 typing practice application built with Python + PySide6. Designed as a production-grade application.

## Features

### 🎯 Practice Features
- **Progressive Training**: Practice lines across multiple levels
- **Dynamic Task Count**: Each level is based on the number of lines in its file
- **Tamil99 Keyboard**: Full Tamil99 keyboard support
- **Keystroke-by-Keystroke Tracking**: Individual keystroke monitoring and guidance
- **Real-time Feedback**: Instant feedback while typing

### 📊 Statistics
- **Accuracy**: Percentage calculation
- **Speed (WPM/SPM)**: Words per minute and strokes per minute
- **Error Tracking**: Monitoring of incorrect keystrokes
- **Progress Saving**: User progress is automatically saved (`~/.thattan/progress.json`)

### 🎨 User Interface
- **Light Theme**: Modern, clean light theme
- **Responsive Design**: Screen size-based font scaling
- **Adaptive Layout**: Keyboard and finger UI automatically adjust to window size, preventing cropping
- **Keyboard Display**: On-screen keyboard display with next key highlighting
- **Finger Guidance**: Visual finger placement guide showing which finger to use for each key
- **Word-by-Word Scrolling**: Scrolling word-by-word for long lines
- **Dynamic Resizing**: Layout adapts in real-time when window is resized

## Installation

### Requirements
- Python 3.8 or higher
- PySide6

### Installation Steps

```bash
# 1. Clone the repository
git clone https://github.com/khaleeljageer/thattan.git
cd thattan

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application (from project root)
python -m thattan
```

## Usage

### Selecting Levels
- Select a level from the level list on the left side
- Each level unlocks after completing the previous level (all levels are open for testing)

### Typing
- The practice line is displayed at the top
- Type in the input box below
- Each keystroke is tracked and feedback is provided for correct/incorrect keystrokes
- The next key is highlighted on the keyboard

### Progress
- Each task is automatically submitted when completed
- Progress is automatically saved
- Progress continues when you reopen the application

## Data Files

### Practice Levels
Practice lines are located in the `thattan/data/levels/` directory:
- `level0.yaml` - Level 0
- `level1.yaml` - Level 1
- `level2.yaml` - Level 2
- `level3.yaml` - Level 3
- `level4.yaml` - Level 4

Each level YAML has a `title` and `content` (list of tasks). The number of items in `content` determines the task count for that level.

### Progress Storage
User progress is saved in the `~/.thattan/progress.json` file.

## Tamil99 Keyboard

This application uses the Tamil99 keyboard layout. All key mappings are embedded in the application, so m17n installation on the system is not required.

### Keyboard Features
- **Keystroke-by-Keystroke Tracking**: Each keystroke is individually tracked
- **Guidance**: The next key is highlighted on the keyboard
- **Shift Key Highlighting**: Highlighted when Shift is required
- **Multi-Keystroke Sequences**: Proper guidance for characters requiring multiple keystrokes (e.g., கா = h+q)
- **Adaptive Sizing**: Keyboard scales dynamically to fit available screen space
- **Font Scaling**: Keyboard fonts automatically adjust based on available width
- **No Cropping**: Layout prevents right-side cropping on smaller screens

## Development

### Structure
```
thattan/                        # ← repo root (git clone creates this)
├── thattan/                    # Python package
│   ├── __main__.py             # python -m thattan entry point
│   ├── app.py                  # Application setup
│   ├── core/
│   │   ├── levels.py           # Level loading from YAML
│   │   ├── progress.py         # Progress storage
│   │   ├── session.py          # Typing session logic
│   │   └── keystroke_tracker.py  # Keystroke tracking
│   ├── ui/
│   │   ├── main_window.py      # Main window & screen management
│   │   ├── colors.py           # Theme colors & utilities
│   │   ├── models.py           # UI data models
│   │   ├── home_widgets.py     # Home screen widgets
│   │   ├── level_cards.py      # Level selection cards
│   │   ├── typing_widgets.py   # Typing practice widgets
│   │   ├── about_overlay.py    # About dialog
│   │   └── custom_overlay.py   # Custom overlay widgets
│   ├── data/
│   │   └── levels/             # Practice level YAML files
│   └── assets/                 # Fonts, images, SVGs
├── tests/                      # Unit tests
├── requirements.txt
├── build_appimage.sh           # AppImage build script
├── thattan.spec                # PyInstaller spec
└── README.md
```

## License

This project is released as open source.

## Contributing

Contributions are welcome! Please send a pull request.

## Resources

- [Tamil99 Keyboard Layout Documentation](https://help.keyman.com/keyboard/ekwtamil99uni/2.0.5/ekwtamil99uni)
- [PySide6 Documentation](https://doc.qt.io/qtforpython/)
