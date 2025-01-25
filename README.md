# Podcast App

This is a Python-based Podcast App with features for managing podcasts, including user login, channel creation, episode management, and audio playback. It is built using PyQt6 for the GUI, SQLite for database management, and Python's built-in libraries for file handling and multimedia playback.

## Features
- **User Login/Registration**: Allows users to sign in or create new accounts.
- **Channel Management**: Users can create, view, and manage podcast channels.
- **Episode Management**: Users can add, delete, and view episodes for each channel.
- **Audio Player**: Play, pause, replay, and control the speed of podcast audio episodes.
- **Drag Window**: The app window can be moved around by clicking and dragging.
- **Delete Episodes**: Users can delete podcast episodes from their channels.

## Requirements
- Python 3.12
- PyQt6
- SQLite (Built-in)

## Installation
1. Install PyQt6:
   ```bash
   pip install PyQt6
   ```
## Setup
* Ensure you have SQLite installed on your system (it comes pre-installed with Python).
* The application creates an SQLite database file called podcast_app.db for storing user and podcast data.
* You can manually add or delete podcast episodes and channels via the app interface.
   
## Usage
1.Run the application:
```
python podcast_app.py
```
2.The app will prompt you to log in or register.

3.Once logged in, you can create new channels, add episodes, and manage your podcasts.

# About podcast.exe
* podcast.exe is developed using pyinstaller.
* PyInstaller is a tool that can be used to convert Python scripts into standalone executable applications. It packages Python code along with all of its dependencies into a single executable file for various platforms like Windows, macOS, and Linux. To make a Windows app you run PyInstaller on Windows, and to make a Linux app you run it on Linux, etc.

## How to develop
1.Install PyInstaller:
```
pip install pyinstaller
```
If there are any issues after installation, add PyInstaller to the environment path.

2.Running PyInstaller: 

Create a folder and place the podcast.py file inside it. Open the folder in VSCode and run the command:
```
pyinstaller --onefile --windowed podcast.py
```
After running the command, you will see two new folders and a new file. Go to the dist folder, and you will find the podcast.exe app."
