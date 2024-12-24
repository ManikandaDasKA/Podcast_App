import os
from tkinter import font
from PyQt6.QtWidgets import ( QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, 
    QLabel, QLineEdit,QListWidget, QFileDialog, QComboBox, QFormLayout, QDialog, QSlider, QListWidgetItem, QMessageBox)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QCursor
import sqlite3
import shutil

class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Login / Register")
        self.user_id = None
        self.setStyleSheet("background-color:rgba(255, 227, 210, 0.96);")
        layout = QVBoxLayout()

        self.username_input = QLineEdit()
        self.username_input.setStyleSheet("padding: 4px 5px; border: 1px solid #ccc; border-radius: 5px;"
        )
        self.username_input.setPlaceholderText("Username")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setStyleSheet("padding: 4px 5px; border: 1px solid #ccc; border-radius: 5px;"
        )
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        button_layout = QHBoxLayout()
        self.login_button = QPushButton("Login")
        self.login_button.setStyleSheet("background-color: rgb(53, 196, 96); color: white; padding:4px 5px; border-radius: 5px;"
        )

        self.register_button = QPushButton("Register")
        self.register_button.setStyleSheet(
        "background-color: rgb(53, 196, 96); color: white; padding:4px 5px; border-radius: 5px;")
        button_layout.addWidget(self.login_button)
        button_layout.addWidget(self.register_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

class DeleteDialog(QDialog):
    def __init__(self, parent, user_id, cursor, conn):
        super().__init__(parent)
        self.setWindowTitle("Delete Episode")
        self.user_id = user_id
        self.cursor = cursor
        self.conn = conn

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Select a channel:"))

        self.delete_list = QListWidget() 
        self.channel_list = QListWidget()
        self.episode_list = QListWidget()

        self.load_channels()
        self.load_episodes()

        self.channel_list.itemClicked.connect(self.display_channel_episodes)
        layout.addWidget(self.channel_list)

        layout.addWidget(QLabel("Select an episode to delete:"))
        self.load_episodes()
        layout.addWidget(self.delete_list)

        self.delete_button = QPushButton("Delete Episode")
        self.delete_button.clicked.connect(self.delete_episode)
        layout.addWidget(self.delete_button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def display_channel_episodes(self, item):
        channel_id = item.data(Qt.ItemDataRole.UserRole)
        if self.user_id:
            self.cursor.execute("SELECT name FROM channels WHERE user_id = ?", (self.user_id,))
            channel_names = self.cursor.fetchall()
            name_of_channel=[channel_name[0] for channel_name in channel_names]
            for i in name_of_channel:
                if str(channel_id) == i:
                    self.load_episodes(channel_id)
                    self.load_delete_episodes1(channel_id)
                else:
                    self.load_episodes(channel_id)

    def load_channels(self):
        self.channel_list.clear()
        try:
            self.cursor.execute("""
                SELECT name FROM channels WHERE user_id = ?
            """, (self.user_id,))
            channels = self.cursor.fetchall()
            for channel in channels:
                item = QListWidgetItem(channel[0])
                item.setData(Qt.ItemDataRole.UserRole, channel[0])  
            
                self.channel_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading channels: {e}")

    def load_episodes(self, channel_id=None):
        self.episode_list.clear()
        if channel_id:
            self.cursor.execute("SELECT title, audio_file FROM episodes WHERE channel_id = ?", (channel_id,))
        else:
            self.cursor.execute("SELECT title, audio_file FROM episodes")

        episodes = self.cursor.fetchall()
        for title, audio_file in episodes:
            self.episode_list.addItem(f"{title} - {audio_file}")

    def load_delete_episodes1(self, channel_id=None):
        self.delete_list.clear()
        if channel_id:
            self.cursor.execute("SELECT channel_id, title, audio_file FROM episodes WHERE channel_id = ?", (channel_id,))
            episodes = self.cursor.fetchall()
            for channelname, title, audio_file in episodes:
                self.delete_list.addItem(f"{channelname} - {title} - {audio_file}")
        else:
            return

    def delete_episode(self):
        selected_item = self.delete_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Warning", "Please select an episode to delete!")
            return

        episode_info = selected_item.text()
        title = episode_info.split(" - ")[1]

        confirm_delete = QMessageBox.question(self, "Confirm Delete", 
            f"Are you sure you want to delete the episode '{title}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if confirm_delete == QMessageBox.StandardButton.Yes:
            try:
                self.cursor.execute("""
                    DELETE FROM episodes 
                    WHERE title = ? 
                    AND id IN (
                        SELECT id FROM channels WHERE user_id = ?
                    )
                """, (title, self.user_id))
                self.conn.commit()

                self.load_delete_episodes1()
                self.load_episodes()
                
                QMessageBox.information(self, "Success", f"Episode '{title}' deleted successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error deleting episode: {e}")
    
class PodcastApp(QMainWindow):
    def __init__(self, user_id=None):
        super().__init__()
        self.setWindowTitle("Podcast App")
        self.setGeometry(100, 100, 600, 600)
        self.user_id = user_id

        title_label = QLabel("Podcast", self)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-family: Papyrus; font-size: 40px; font-weight: bold; color: rgba(247, 105, 129, 0.96);")

        self.episode_list = QListWidget() 
        self.delete_list = QListWidget() 
        self.delete_episode_layout = None
        self.init_db()

        self.drag_start_position = None

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.addWidget(title_label)

        self.style()
        self.create_channel_section()
        self.create_episode_section()
        self.create_audio_player()
        self.add_logout_and_exit()
        self.load_channels()
        self.load_channels1()

    def init_db(self):
        self.conn = sqlite3.connect("podcast_app.db")
        self.cursor = self.conn.cursor()

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                password TEXT
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                user_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER,
                channel_id TEXT,
                title TEXT,
                audio_file TEXT,
                FOREIGN KEY(id) REFERENCES channels(id)
            )
        """)
        self.conn.commit()

    def style(self):
        self.setStyleSheet("""
            QWidget {
            background-color:rgba(255, 227, 210, 0.96);
            }
            QSlider::groove:horizontal {
                border: 1px solid #bbb;
                background: #eee;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                border: 1px solid #5c5c5c;
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal:hover {
                background: #1abc9c;
            }
            QSlider::sub-page:horizontal {
                background: #3498db;
                border-radius: 4px;
            }
            QSlider::add-page:horizontal {
                background: #ccc;
                border-radius: 4px;
            }
            QPushButton {   
            background-color:rgb(53, 196, 96);
            color: white;
            border: none;
            border-radius: 5px;
            padding: 4px 5px;
            text-align: center;
            font-size: 12px;
            }
            QLineEdit {
            padding: 4px 5px;
            border: 1px solid #ccc;
            border-radius: 5px;
            }
            QLabel {
            font-size: 13px;
            }
            QComboBox {
            padding: 4px 5px;
            border: 1px solid #ccc;
            border-radius: 5px;
            }
            QComboBox::down-arrow {
            width: 8px;
            height: 8px;
            }
        """)

    def create_channel_section(self):

        channel_layout = QHBoxLayout()
        add_channel_layout = QHBoxLayout()

        self.channel_list = QListWidget()
        self.channel_list.itemClicked.connect(self.display_channel_episodes)
        channel_layout.addWidget(QLabel("Channels:"))
        channel_layout.addWidget(self.channel_list)
        
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("Create a channel")
        add_channel_layout.addWidget(self.channel_input)

        add_channel_btn = QPushButton("Add Channel")
        add_channel_btn.clicked.connect(self.add_channel)
        add_channel_btn.setFixedSize(80, 27)
        add_channel_layout.addWidget(add_channel_btn)
        channel_layout.addLayout(add_channel_layout)

        self.main_layout.addLayout(channel_layout)

    def create_episode_section(self):
        audio_file_layout = QHBoxLayout()
        episode_layout = QFormLayout()

        self.episode_channel_dropdown = QComboBox()

        self.load_channels()

        episode_layout.addRow("Channel:", self.episode_channel_dropdown)

        self.episode_title_input = QLineEdit()
        self.episode_title_input.setPlaceholderText("Episode Title")

        episode_layout.addRow("Title:", self.episode_title_input)
        self.audio_file_path = QLineEdit()
        self.audio_file_path.setPlaceholderText("Audio File Path")
        browse_audio_btn = QPushButton("Browse")
        browse_audio_btn.setFixedSize(80, 27)
        browse_audio_btn.clicked.connect(self.browse_audio_file)
        audio_file_layout.addWidget(self.audio_file_path)
        audio_file_layout.addWidget(browse_audio_btn)
        episode_layout.addRow("Audio:", audio_file_layout)

        action_button_layout = QHBoxLayout()
        add_episode_btn = QPushButton("Add Episode")
        add_episode_btn.setFixedSize(100,30)
        add_episode_btn.clicked.connect(self.add_episode)
        refresh_btn = QPushButton("  Refresh  ")
        refresh_btn.setFixedSize(100, 30)
        refresh_btn.clicked.connect(self.load_episodes)
        action_button_layout.addWidget(add_episode_btn, alignment=Qt.AlignmentFlag.AlignRight)
        action_button_layout.addWidget(refresh_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        episode_layout.addRow("", action_button_layout)

        self.main_layout.addLayout(episode_layout)

        self.episode_list = QListWidget()
        self.episode_list.itemClicked.connect(self.play_episode)
        self.main_layout.addWidget(QLabel('Play List'))
        self.main_layout.addWidget(self.episode_list)

    def load_channels(self):
        self.channel_list.clear()
        self.cursor.execute("SELECT id, name FROM channels")
        channels = self.cursor.fetchall()
        for channel_id, channel_name in channels:
            item = QListWidgetItem(channel_name)
            item.setData(Qt.ItemDataRole.UserRole, channel_name)
            self.channel_list.addItem(item)

    def load_channels1(self):
        self.episode_channel_dropdown.clear()
        self.cursor.execute("SELECT id, name FROM channels WHERE user_id = ?", (self.user_id,))
        channels = self.cursor.fetchall()
        self.episode_channel_dropdown.addItems([channel[1] for channel in channels])
        self.load_episodes()
    
    def load_channels2(self):
        self.cursor.execute("SELECT id, name FROM channels WHERE user_id = ?", (self.user_id,))
        channels = self.cursor.fetchall()
        self.episode_channel_dropdown.addItems([channel[1] for channel in channels])
        self.load_episodes()

    def display_channel_episodes(self, item):
        channel_id = item.data(Qt.ItemDataRole.UserRole)
        if self.user_id:
            self.cursor.execute("SELECT name FROM channels WHERE user_id = ?", (self.user_id,))
            channel_names = self.cursor.fetchall()
            name_of_channel=[channel_name[0] for channel_name in channel_names]
            if str(channel_id) == name_of_channel[0]:
                self.load_delete_episodes(channel_id)
                self.load_episodes(channel_id)
            else:
                self.load_episodes(channel_id)
        else:
            self.load_episodes(channel_id) 

    def load_episodes(self, channel_id=None):
        self.episode_list.clear()
        if channel_id:
            self.cursor.execute("SELECT title, audio_file FROM episodes WHERE channel_id = ?", (channel_id,))
        else:
            self.cursor.execute("SELECT title, audio_file FROM episodes")

        episodes = self.cursor.fetchall()
        for title, audio_file in episodes:
            self.episode_list.addItem(f"{title} - {audio_file}")

    def add_channel(self):
        if not self.user_id:
            self.statusBar().showMessage("You must log in to create a channel!")
            return

        channel_name = self.channel_input.text().strip()
        if not channel_name:
            self.statusBar().showMessage("Channel name cannot be empty!")
            return

        try:
            self.cursor.execute("INSERT INTO channels (name, user_id) VALUES (?, ?)", (channel_name, self.user_id))
            self.conn.commit()
            self.channel_input.clear()
            self.load_channels()
            self.statusBar().showMessage(f"Channel '{channel_name}' created successfully!")
            self.load_channels1() 
            
        except sqlite3.IntegrityError:
            self.statusBar().showMessage(f"Channel '{channel_name}' already exists!")

    def add_episode(self):
        if not self.user_id:
            self.statusBar().showMessage("You must log in to add episodes!")
            return

        channel_id = self.episode_channel_dropdown.currentText()
        title = self.episode_title_input.text()
        audio_file = self.audio_file_path.text()

        if not all([channel_id, title, audio_file]):
            self.statusBar().showMessage("All fields are required!")
            return

        try:
            user_directory = os.path.join("uploads", str(self.user_id), str(title))
            os.makedirs(user_directory, exist_ok=True)

            destination_file = os.path.join(user_directory, os.path.basename(audio_file))
            try:
                shutil.copy(audio_file, destination_file)
            except Exception as e:
                self.statusBar().showMessage(f"Failed to copy file: {e}")
                return

            self.cursor.execute("SELECT id FROM channels WHERE name = ?", (channel_id,))
            episode_id = self.cursor.fetchall()[0]
            episode_id1=episode_id[0]
            self.cursor.execute("INSERT INTO episodes (id, channel_id, title, audio_file) VALUES (?, ?, ?, ?)",
                                (episode_id1, channel_id, title, destination_file))
            self.conn.commit()
            self.episode_title_input.clear()
            self.audio_file_path.clear()
            self.load_episodes(channel_id)
            self.load_delete_episodes(channel_id)
            self.statusBar().showMessage(f"Episode '{title}' added successfully!")
        except sqlite3.IntegrityError:
            self.statusBar().showMessage(f"Episode '{title}' already exists!")

    def load_delete_episodes(self, channel_id=None):
        self.delete_list.clear()
        if channel_id:
            self.cursor.execute("SELECT channel_id, title, audio_file FROM episodes WHERE channel_id = ?", (channel_id,))
            episodes = self.cursor.fetchall()
            for channelname, title, audio_file in episodes:
                    self.delete_list.addItem(f"{channelname} - {title} - {audio_file}")
        else:
            return
        
    def browse_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "", "Audio Files (*.mp3 *.wav)")
        if file_path:
            self.audio_file_path.setText(file_path)

    def create_audio_player(self):
        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_output)

        audio_player_layout = QVBoxLayout()

        self.player_status = QLabel(" ")
        audio_player_layout.addWidget(self.player_status)

        self.audio_slider = QSlider(Qt.Orientation.Horizontal)
        self.audio_slider.setRange(0, 0) 
        self.audio_slider.sliderMoved.connect(self.seek_audio) 
        self.audio_slider.sliderPressed.connect(self.pause_slider)
        self.audio_slider.sliderReleased.connect(self.resume_slider)
        audio_player_layout.addWidget(self.audio_slider)

        button_layout = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.setFixedSize(100, 30)
        self.pause_button = QPushButton("Pause")
        self.pause_button.setFixedSize(100, 30)
        self.replay_button = QPushButton("Replay")
        self.replay_button.setFixedSize(100, 30)
        self.speed_button = QPushButton("Speed: 1x")
        self.speed_button.setFixedSize(100, 30)

        self.play_button.clicked.connect(self.audio_player.play)
        self.pause_button.clicked.connect(self.audio_player.pause)
        self.replay_button.clicked.connect(self.replay_audio)
        self.speed_button.clicked.connect(self.change_speed)

        button_layout.addWidget(self.play_button, alignment=Qt.AlignmentFlag.AlignRight)
        button_layout.addWidget(self.pause_button, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addWidget(self.replay_button, alignment=Qt.AlignmentFlag.AlignCenter)
        button_layout.addWidget(self.speed_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.audio_duration_label = QLabel("00:00 / 00:00")
        self.audio_player.durationChanged.connect(self.update_duration)
        self.audio_player.positionChanged.connect(self.update_position)

        audio_player_layout.addWidget(self.audio_duration_label)
        audio_player_layout.addLayout(button_layout)

        self.main_layout.addLayout(audio_player_layout)

        self.audio_slider.sliderMoved.connect(self.seek_audio) 
        self.audio_slider.sliderPressed.connect(self.pause_slider)  
        self.audio_slider.sliderReleased.connect(self.resume_slider)  

    def mousePressEvent(self, event):
      if event.button() == Qt.MouseButton.LeftButton:
        self.drag_start_position = event.globalPosition()
        self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))

    def drag_start_position(self):
        pass

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton and self.drag_start_position:
            delta = event.globalPosition() - self.drag_start_position
            self.move(self.pos() + delta.toPoint())  
            self.drag_start_position = event.globalPosition()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_position = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def seek_audio(self, position):
        self.audio_player.setPosition(position * 1000) 
        current_minutes, current_seconds = divmod(position, 60)
        total_minutes, total_seconds = divmod(self.total_duration, 60)
        self.audio_duration_label.setText(
            f"{current_minutes:02}:{current_seconds:02} / {total_minutes:02}:{total_seconds:02}"
        )

    def pause_slider(self):          
        self.audio_player.pause()
        if self.audio_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.was_playing = True
            self.audio_player.pause()
        else:
            self.was_playing = False
    
    def pause_audio(self):
        self.audio_player.pause()
        if self.audio_player.state() == QMediaPlayer.PlayingState:
            self.was_playing = True
            self.audio_player.pause()
        else:
            self.was_playing = False

    def resume_slider(self):
        if self.was_playing:
            self.audio_player.play()

    def update_duration(self, duration):
        self.total_duration = duration // 1000
        self.audio_slider.setRange(0, self.total_duration) 
        self.update_position(self.audio_player.position())

    def update_position(self, position):
        current_position = position // 1000
        self.audio_slider.setValue(current_position) 
        total_minutes, total_seconds = divmod(self.total_duration, 60)
        current_minutes, current_seconds = divmod(current_position, 60)
        self.audio_duration_label.setText(f"{current_minutes:02}:{current_seconds:02} / {total_minutes:02}:{total_seconds:02}")

    def play_episode(self, item):
        episode_info = item.text()
        audio_file = episode_info.split(" - ")[-1]
        if os.path.exists(audio_file):
            self.audio_player.setSource(QUrl.fromLocalFile(audio_file))
            self.audio_player.play()
            audio_file=audio_file.split("\\")[-1]
            self.player_status.setText(f"Playing: {audio_file}")
        else:
            self.player_status.setText("Audio file not found!")

    def replay_audio(self):
        self.audio_player.setPosition(0)
        self.audio_player.play()

    def change_speed(self):
        current_rate = self.audio_player.playbackRate()
        new_rate = 1.5 if current_rate == 1 else 1
        self.audio_player.setPlaybackRate(new_rate)
        self.speed_button.setText(f"Speed: {new_rate}x")

    def add_logout_and_exit(self):
        button_layout = QHBoxLayout()

        login_button = QPushButton("Login/Register")
        login_button.clicked.connect(self.show_login_form)
        login_button.setFixedSize(100, 30)
        button_layout.addWidget(login_button,alignment=Qt.AlignmentFlag.AlignRight)

        logout_button = QPushButton("Logout")
        logout_button.clicked.connect(self.logout)
        logout_button.setFixedSize(100, 30)
        button_layout.addWidget(logout_button, alignment=Qt.AlignmentFlag.AlignCenter)

        logout_button = QPushButton("Episode Delete")
        logout_button.clicked.connect(self.open_delete_dialog)
        logout_button.setFixedSize(100, 30)
        button_layout.addWidget(logout_button, alignment=Qt.AlignmentFlag.AlignCenter)

        close_button = QPushButton("Close App")
        close_button.clicked.connect(self.close_app)
        close_button.setFixedSize(100, 30)
        button_layout.addWidget(close_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.main_layout.addLayout(button_layout)

    def show_login_form(self):
        self.login_dialog = LoginDialog() 
        self.login_dialog.login_button.clicked.connect(self.handle_login)
        self.login_dialog.register_button.clicked.connect(self.handle_registration)
        self.login_dialog.exec() 

    def handle_login(self):
        username = self.login_dialog.username_input.text()
        password = self.login_dialog.password_input.text()

        self.cursor.execute("SELECT id FROM users WHERE name = ? AND password = ?", (username, password))
        result = self.cursor.fetchone()

        if result:
            self.user_id = result[0]
            self.statusBar().showMessage(f"Welcome back, {username}!")
            self.login_dialog.accept() 
            self.load_channels1()      
            self.load_delete_episodes()
              
        else:
            self.statusBar().showMessage("Invalid username or password!")

    def handle_registration(self):
        username = self.login_dialog.username_input.text()
        password = self.login_dialog.password_input.text()

        try:
            self.cursor.execute("INSERT INTO users (name, password) VALUES (?, ?)", (username, password))
            self.conn.commit()
            self.statusBar().showMessage(f"User {username} registered successfully!")
            self.login_dialog.accept() 
        except sqlite3.IntegrityError:
            self.statusBar().showMessage("Username already exists. Please choose another one.")


    def logout(self):
        if not self.user_id:
            self.statusBar().showMessage("You are not logged in!")
            return
        self.user_id = None
        self.statusBar().showMessage("Logged out successfully!")
        self.load_channels1()
      
    def open_delete_dialog(self):
        if not self.user_id:
            self.statusBar().showMessage("You must log in to delete episodes!")
            return

        dialog = DeleteDialog(self, self.user_id, self.cursor, self.conn)
        dialog.exec()

    def close_app(self):
        QApplication.instance().quit()

def authenticate_user():
    conn = sqlite3.connect("podcast_app.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()

    dialog = LoginDialog()
    dialog.login_button.clicked.connect(lambda: login_user(dialog, cursor, conn))
    dialog.register_button.clicked.connect(lambda: register_user(dialog, cursor, conn))

    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.user_id
    return None

def login_user(dialog, cursor, conn):
    username = dialog.username_input.text()
    password = dialog.password_input.text()

    cursor.execute("SELECT id FROM users WHERE name = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    if user:
        dialog.user_id = user[0]

        user_directory = os.path.join("uploads", str(user[0]))
        os.makedirs(user_directory, exist_ok=True)

        dialog.accept()
    else:
        dialog.username_input.clear()
        dialog.password_input.clear()
        dialog.setWindowTitle("Invalid credentials. Try again.")

def register_user(dialog, cursor, conn):
    username = dialog.username_input.text()
    password = dialog.password_input.text()

    try:
        cursor.execute("INSERT INTO users (name, password) VALUES (?, ?)", (username, password))
        conn.commit()
        cursor.execute("SELECT id FROM users WHERE name = ?", (username,))
        user = cursor.fetchone()
        if user:
            user_directory = os.path.join("uploads", str(user[0]))
            os.makedirs(user_directory, exist_ok=True)
        dialog.setWindowTitle("Registration successful. Please login.")
    except sqlite3.IntegrityError:
        dialog.setWindowTitle("User already exists. Try a different username.")

def main():
    app = QApplication([])
    skip_login = True  

    if skip_login:
        user_id = None 
    else:
        user_id = authenticate_user()

    main_window = PodcastApp(user_id)
    main_window.show()
    app.exec()

if __name__ == "__main__":
    main()