import sys
import threading
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
from scipy.io.wavfile import write
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QSound
from PyQt5.QtCore import QUrl
from main_ui import Ui_MainWindow  # Import the generated class
import matplotlib.pyplot as plt
import wave
import io


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setupUi(self)

        self.sample_rate = 25600  # Sample rate for WAV files
        self.data = self.get_data()  # Fetch initial data from CSV

        # Dictionary to store start times for each location
        self.location_start_times = {}
        image_widget = getattr(self, "lblMediaIcon", None)
        if image_widget:
            image_widget.setPixmap(QPixmap('images/med.png'))

        # Initialize media player
        self.media_player = QMediaPlayer()
        self.media_player.setNotifyInterval(1000)  # Update every second

        # Connect media player signals to update UI
        self.media_player.positionChanged.connect(self.update_progress)
        self.media_player.durationChanged.connect(self.update_duration)
        self.media_player.mediaStatusChanged.connect(self.media_status_changed)

        # Connect play/pause button
        self.btnPlayPause.clicked.connect(self.toggle_play_pause)

        # Data structure to keep track of the last 5 entries for each location
        self.history = {
            'L1_S1': [],
            'L1_S2': [],
            'L2_S1': [],
            'L2_S2': [],
            'L3_S1': [],
            'L3_S2': [],
            'L4_S1': [],
            'L4_S2': []
        }

        # Timer to check for result CSV every 10 seconds
        self.result_timer = QTimer(self)
        self.result_timer.timeout.connect(self.check_result_csv)

        # Start the timer immediately
        self.result_timer.start(10000)

        # Connect buttons to their respective slots
        self.L1_S1_listen_pushButton.clicked.connect(lambda: self.on_button_click('L1_S1'))
        self.L1_S2_listen_pushButton.clicked.connect(lambda: self.on_button_click('L1_S2'))
        self.L2_S1_listen_pushButton.clicked.connect(lambda: self.on_button_click('L2_S1'))
        self.L2_S2_listen_pushButton.clicked.connect(lambda: self.on_button_click('L2_S2'))
        self.L3_S1_listen_pushButton.clicked.connect(lambda: self.on_button_click('L3_S1'))
        self.L3_S2_listen_pushButton.clicked.connect(lambda: self.on_button_click('L3_S2'))
        self.L4_S1_listen_pushButton.clicked.connect(lambda: self.on_button_click('L4_S1'))
        self.L4_S2_listen_pushButton.clicked.connect(lambda: self.on_button_click('L4_S2'))

        self.L1_S1_graph_pushButton.clicked.connect(lambda: self.plot_waveform('L1_S1'))
        self.L1_S2_graph_pushButton.clicked.connect(lambda: self.plot_waveform('L1_S2'))
        self.L2_S1_graph_pushButton.clicked.connect(lambda: self.plot_waveform('L2_S1'))
        self.L2_S2_graph_pushButton.clicked.connect(lambda: self.plot_waveform('L2_S2'))
        self.L3_S1_graph_pushButton.clicked.connect(lambda: self.plot_waveform('L3_S1'))
        self.L3_S2_graph_pushButton.clicked.connect(lambda: self.plot_waveform('L3_S2'))
        self.L4_S1_graph_pushButton.clicked.connect(lambda: self.plot_waveform('L4_S1'))
        self.L4_S2_graph_pushButton.clicked.connect(lambda: self.plot_waveform('L4_S2'))

        self.btnBack.clicked.connect(lambda: self.back_to_mainscreen())
        self.btnBack_2.clicked.connect(lambda: self.back_to_mainscreen_2())


    def get_data(self):
        folder = Path('data') / 'input'
        if not folder.exists():
            raise FileNotFoundError(f"The specified folder does not exist: {folder}")

        try:
            read_file = max(folder.glob('*'), key=lambda p: p.stat().st_ctime)
        except ValueError:
            raise FileNotFoundError(f"No files found in the specified folder: {folder}")

        df = pd.read_csv(read_file)

        data = {
            'L1_S1': df['Location1_Sample1'],
            'L1_S2': df['Location1_Sample2'],
            'L2_S1': df['Location2_Sample1'],
            'L2_S2': df['Location2_Sample2'],
            'L3_S1': df['Location3_Sample1'],
            'L3_S2': df['Location3_Sample2'],
            'L4_S1': df['Location4_Sample1'],
            'L4_S2': df['Location4_Sample2']
        }

        return data

    def check_result_csv(self):
        try:
            folder = Path('data') / 'result'
            if not folder.exists():
                folder.mkdir()

            result_files = list(folder.glob('*.csv'))
            if not result_files:
                print("No result CSV file found. Sleeping for 5 seconds.")
                return

            # Get the newest result CSV file
            newest_file = max(result_files, key=lambda f: f.stat().st_mtime)

            # Read and process the CSV file
            df = pd.read_csv(newest_file)
            print(f"Found result CSV file: {newest_file}")

            # Update the history with the new row
            self.update_history(df)

            # Display the data from the CSV file on the UI (example: filling a table)
            self.display_result_data(df)
        except Exception as e:
            print(f"Error in check_result_csv: {e}")

    def update_history(self, df):
        try:
            # Map the button IDs to the corresponding columns in the CSV
            column_map = {
                'L1_S1': 'Location1_Sample1',
                'L1_S2': 'Location1_Sample2',
                'L2_S1': 'Location2_Sample1',
                'L2_S2': 'Location2_Sample2',
                'L3_S1': 'Location3_Sample1',
                'L3_S2': 'Location3_Sample2',
                'L4_S1': 'Location4_Sample1',
                'L4_S2': 'Location4_Sample2'
            }

            # Append the latest entry to the history and maintain only the last 5 entries
            for button_id in column_map.keys():
                column_name = column_map[button_id]
                latest_entry = df[column_name].values[0]
                self.history[button_id].append(int(latest_entry))
                if len(self.history[button_id]) > 5:
                    self.history[button_id].pop(0)
        except Exception as e:
            print(f"Error in update_history: {e}")

    def display_result_data(self, df):
        try:
            # Extract and display the last 5 entries for each location
            for button_id in self.history:
                if button_id == "L1_S1" or button_id == "L1_S2":
                    loc = df['Loc1'].iloc[0]
                elif button_id == "L2_S1" or button_id == "L2_S2":
                    loc = df['Loc2'].iloc[0]
                elif button_id == "L3_S1" or button_id == "L3_S2":
                    loc = df['Loc3'].iloc[0]
                elif button_id == "L4_S1" or button_id == "L4_S2":
                    loc = df['Loc4'].iloc[0]
                self.update_loc_display(button_id, button_id, loc)
        except Exception as e:
            print(f"Error in display_result_data: {e}")

    def update_loc_display(self, button_id, loc, locNum):
        try:
            # Assuming the labels are named as provided
            label_widget = getattr(self, f"{button_id}_input_label")
            # Translate and display the last 5 entries for the location
            translated_entries = [self.translate_loc_value(val) for val in self.history[button_id]]
            label_widget.setText(",".join(translated_entries))
            finalres = self.translate_loc_value(locNum)

            # Set the image based on the latest entry
            if locNum is not None:
                image_path = f"images/{finalres.lower()}.png"
                id = button_id.split('_')[0]
                image_widget = getattr(self, f"{id}_image_label", None)
                if image_widget:
                    image_widget.setPixmap(QPixmap(image_path))
        except Exception as e:
            print(f"Error in update_loc_display: {e}")

    def translate_loc_value(self, value):
        try:
            # Translate numeric values to text
            loc_dict = {0: "Car", 1: "Kids", 2: "Mower", 3: "Dog"}
            return loc_dict.get(value, "Unknown")
        except Exception as e:
            print(f"Error in translate_loc_value: {e}")
            return "Unknown"

    def save_wav(self, filename, data, sample_rate):
        try:
            # Scale the data to 16-bit integers (-32768 to 32767)
            scaled_data = np.int16(data * 32767)
            write(filename, sample_rate, scaled_data)
            print(f"WAV file saved at: {filename}")
        except Exception as e:
            print(f"Error in save_wav: {e}")

    def play_sound(self, filename):
        try:
            print(f"Playing sound from file: {filename}")
            QSound.play(filename)
        except Exception as e:
            print(f"Error in play_sound: {e}")
    def back_to_mainscreen_2(self):
            self.stackedWidget.setCurrentIndex(0)
    def back_to_mainscreen(self):
        self.media_player.stop()  # Reset media player state
        self.stackedWidget.setCurrentIndex(0)

    def on_button_click(self, button_id):
        try:
            # Update the lblListenHeader based on the button_id
            location, sample = button_id.split('_')
            self.lblListenHeader.setText(f"Location {location[1]} Sample {sample[1]}")
            self.stackedWidget.setCurrentIndex(1)
            street_noise_data = self.data[button_id].to_numpy()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                self.save_wav(temp_file.name, street_noise_data, self.sample_rate)
                temp_file_path = temp_file.name
                print(f"Temporary WAV file created at: {temp_file_path}")

            # Load the audio sample into the media player
            self.load_audio(temp_file_path)

        except Exception as e:
            print(f"Error in on_button_click: {e}")

    def load_audio(self, filename):
        try:
            if self.media_player.state() == QMediaPlayer.PlayingState:
                self.media_player.stop()
            media_content = QMediaContent(QUrl.fromLocalFile(filename))
            self.media_player.setMedia(media_content)
            self.media_player.play()
        except Exception as e:
            print(f"Error in load_audio: {e}")

    def media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.media_player.stop()

    def toggle_play_pause(self):
        if self.media_player.state() == QMediaPlayer.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()

    def update_progress(self, position):
        self.lblRunningTime.setText(self.format_time(position))
        self.progressBar.setValue(position)

    def update_duration(self, duration):
        self.lblTotalTime.setText(self.format_time(duration))
        self.progressBar.setMaximum(duration)

    @staticmethod
    def format_time(ms):
        seconds = (ms // 1000) % 60
        minutes = (ms // 60000) % 60
        hours = (ms // 3600000)
        if hours > 0:
            return f"{hours}:{minutes:02}:{seconds:02}"
        else:
            return f"{minutes}:{seconds:02}"

    def plot_waveform(self, button_id):
        try:
            # Fetch the audio data
            street_noise_data = self.data[button_id].to_numpy()
            location, sample = button_id.split('_')
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                self.save_wav(temp_file.name, street_noise_data, self.sample_rate)
                temp_file_path = temp_file.name

            # Read and plot the waveform
            spf = wave.open(temp_file_path, "r")
            signal = spf.readframes(-1)
            signal = np.frombuffer(signal, np.int16)
            fs = spf.getframerate()

            if spf.getnchannels() == 2:
                print("Just mono files")
                return

            Time = np.linspace(0, len(signal) / fs, num=len(signal))

            # Create a plot and save it to a buffer
            plt.figure()
            loc=f"Location {location[1]} Sample {sample[1]}"
            plt.title(f"Signal Wave - {loc}")
            plt.plot(Time, signal)
            plt.xlabel("Time (s)")
            plt.ylabel("Amplitude")

            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            plt.close()
            buf.seek(0)

            # Load the buffer into a QPixmap
            pixmap = QPixmap()
            pixmap.loadFromData(buf.getvalue())

            # Set the pixmap to the QLabel and switch to the page with the graph
            self.lblGraph.setPixmap(pixmap)
            self.stackedWidget.setCurrentIndex(2)

        except Exception as e:
            print(f"Error in plot_waveform: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
