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
- **Progress Saving**: User progress is automatically saved (`~/.ezhuthaali/progress.json`)

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
git clone <repository-url>
cd ezhuthaali

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Linux/macOS:
source .venv/bin/activate
# Windows:
# .venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
python app.py
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
Practice lines are located in the `ezhuthaali/data/levels/` directory:
- `level0.txt` - Level 0
- `level1.txt` - Level 1
- `level2.txt` - Level 2
- `level3.txt` - Level 3
- `level4.txt` - Level 4

Each line in a file = one practice task. The number of lines in the file determines the task count for that level.

### Progress Storage
User progress is saved in the `~/.ezhuthaali/progress.json` file.

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
ezhuthaali/
├── app.py                 # Application entry point
├── ezhuthaali/
│   ├── core/
│   │   ├── levels.py      # Level management
│   │   ├── progress.py    # Progress storage
│   │   ├── session.py     # Typing session
│   │   └── keystroke_tracker.py  # Keystroke tracking
│   ├── ui/
│   │   └── main_window.py # Main UI
│   └── data/
│       └── levels/        # Practice level files
└── requirements.txt
```

## License

This project is released as open source.

## Contributing

Contributions are welcome! Please send a pull request.

## Resources

- [Tamil99 Keyboard Layout Documentation](https://help.keyman.com/keyboard/ekwtamil99uni/2.0.5/ekwtamil99uni)
- [PySide6 Documentation](https://doc.qt.io/qtforpython/)
