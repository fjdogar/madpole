# GUI imports
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QSoundEffect
from PyQt5.QtCore import Qt, QTimer, QUrl

from datetime import datetime

# OS imports - these should probably be moved somewhere else
import os
import sys
import string
import threading
import queue
import shutil
# Feature imports
import frogtool
import tadpole_functions
import requests
import wave
from io import BytesIO
import psutil
import json
import time
from bs4 import BeautifulSoup

basedir = os.path.dirname(__file__)

static_NoDrives = "N/A"
static_AllSystems = "ALL"

def RunFrogTool():
    drive = window.combobox_drive.currentText()
    console = window.combobox_console.currentText()
    
    print(f"Running frogtool with drive ({drive}) and console ({console})")
    try:
        #should probably replace this with with rebuilding the favourites list at some point
        tadpole_functions.emptyFavourites(drive)
        tadpole_functions.emptyHistory(drive)
        total_roms = 0
        if(console == static_AllSystems):
            for console in frogtool.systems.keys():
                result = frogtool.process_sys(drive, console, False)
            #TODO: eventually we could return a total roms across all systems, but not sure users will care
            QMessageBox.about(window, "Result", "Rebuilt all roms for all systems")
        else:
            result = frogtool.process_sys(drive, console, False)
            processGameShortcuts()       
            QMessageBox.about(window, "Result", result)        
        #remember to reload table if we delete any files
        loadROMsToTable()
    except frogtool.StopExecution:
        pass

def processGameShortcuts():
    drive = window.combobox_drive.currentText()
    console = window.combobox_console.currentText()
    for i in range(window.tbl_gamelist.rowCount()):
        comboBox = window.tbl_gamelist.cellWidget(i, 4)
        #if its blank, it doesn't have a position so move on
        if comboBox.currentText() == '':
            continue
        else:
            position = int(comboBox.currentText())
            #position is 0 based
            position = position - 1
            game = window.tbl_gamelist.item(i, 0).text()
            #print(drive + " " + console + " " + str(position) + " "+ game)
            tadpole_functions.changeGameShortcut(drive, console, position, game)

def reloadDriveList():
    current_drive = window.combobox_drive.currentText()
    window.combobox_drive.clear()

    for drive in psutil.disk_partitions():
        if os.path.exists(os.path.join(drive.mountpoint, "bios", "bisrv.asd")):
            window.combobox_drive.addItem(QIcon(window.style().standardIcon(QStyle.StandardPixmap.SP_DriveHDIcon)),
                                          drive.mountpoint,
                                          drive.mountpoint)

    if len(window.combobox_drive) > 0:
        toggle_features(True)
        window.status_bar.showMessage("SF2000 Drive(s) Detected.", 20000)

    else:
        # disable functions
        window.combobox_drive.addItem(QIcon(), static_NoDrives, static_NoDrives)
        window.status_bar.showMessage("No SF2000 Drive Detected. Click refresh button to try again.", 20000)
        toggle_features(False)

    window.combobox_drive.setCurrentText(current_drive)


def toggle_features(enable: bool):
    """Toggles program features on or off"""
    features = [window.btn_update,
                window.combobox_console,
                window.combobox_drive,
                window.menu_os,
                window.menu_bgm,
                window.menu_consoleLogos,
                window.menu_boxart,
                window.menu_roms,
                window.tbl_gamelist]

    for feature in features:
        feature.setEnabled(enable)

def loadROMsToTable():
    print("loading roms to table")
    drive = window.combobox_drive.currentText()
    system = window.combobox_console.currentText()
    if drive == static_NoDrives or system == "???" or system == static_AllSystems:
        #TODO: should load ALL ROMs to the table rather than none
        window.tbl_gamelist.setRowCount(0)
        return
    roms_path = os.path.join(drive, system)
    try:
        files = frogtool.getROMList(roms_path)
        window.tbl_gamelist.setRowCount(len(files))
        print(f"found {len(files)} ROMs")
        for i,f in enumerate(files):
            humanReadableFileSize = "ERROR"
            filesize = os.path.getsize(os.path.join(roms_path, f))           
            if filesize > 1024*1024:  # More than 1 Megabyte
                humanReadableFileSize = f"{round(filesize/(1024*1024),2)} MB"
            elif filesize > 1024:  # More than 1 Kilobyte
                humanReadableFileSize = f"{round(filesize/1024,2)} KB"
            else:  # Less than 1 Kilobyte
                humanReadableFileSize = f"filesize Bytes"
            
            # Filename
            cell_filename = QTableWidgetItem(f"{f}")
            cell_filename.setTextAlignment(Qt.AlignVCenter)
            cell_filename.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            window.tbl_gamelist.setItem(i, 0, cell_filename)  
            #Filesize
            cell_fileSize = QTableWidgetItem(f"{humanReadableFileSize}")
            cell_fileSize.setTextAlignment(Qt.AlignCenter)
            cell_fileSize.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            window.tbl_gamelist.setItem(i, 1, cell_fileSize) 
            # View Thumbnail Button 
            cell_viewthumbnail = QTableWidgetItem(f"View")
            cell_viewthumbnail.setTextAlignment(Qt.AlignCenter)
            cell_viewthumbnail.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            window.tbl_gamelist.setItem(i, 2, cell_viewthumbnail)     
            # View Delete Button 
            cell_delete = QTableWidgetItem(f"Delete")
            cell_delete.setTextAlignment(Qt.AlignCenter)
            cell_delete.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
            window.tbl_gamelist.setItem(i, 3, cell_delete)
            # Add to Shortcuts
            shortcut_comboBox = QComboBox()
            shortcut_comboBox.addItem("")
            shortcut_comboBox.addItem("1")
            shortcut_comboBox.addItem("2")
            shortcut_comboBox.addItem("3")
            shortcut_comboBox.addItem("4")
            cell_shortcuts = window.tbl_gamelist.setCellWidget(i, 4, shortcut_comboBox)
            shortcut_comboBox.activated.connect(window.validateGameShortcutComboBox)
        print("finished loading roms to table")    
        # Adjust column widths
        #window.tbl_gamelist
    except frogtool.StopExecution:
        # Empty the table
        window.tbl_gamelist.setRowCount(0)
        print("frogtool stop execution on table load caught")
        
    window.tbl_gamelist.show()

def catchTableCellClicked(clickedRow, clickedColumn):
    print(f"clicked view thumbnail for {clickedRow},{clickedColumn}")
    drive = window.combobox_drive.currentText()
    system = window.combobox_console.currentText()
    if window.tbl_gamelist.horizontalHeaderItem(clickedColumn).text() == "Thumbnail":  #view thumbnail
        gamename = window.tbl_gamelist.item(clickedRow, 0).text()
        viewThumbnail(os.path.join(drive, system, gamename))
    elif window.tbl_gamelist.horizontalHeaderItem(clickedColumn).text() == "Delete ROM": 
        gamename = window.tbl_gamelist.item(clickedRow, 0).text()
        deleteROM(os.path.join(drive, system, gamename))

def viewThumbnail(rom_path):
    window.window_thumbnail = thumbnailWindow(rom_path)  
    result = window.window_thumbnail.exec()
    if result:
        newLogoFileName = window.window_thumbnail.new_viewer.path
        print(f"user tried to load image: {newLogoFileName}")
        if newLogoFileName is None or newLogoFileName == "":
            print("user cancelled image select")
            return

        try:
            tadpole_functions.changeZXXThumbnail(rom_path, newLogoFileName)
        except tadpole_functions.Exception_InvalidPath:
            QMessageBox.about(window, "Change ROM Cover", "An error occurred.")
            return
        QMessageBox.about(window, "Change ROM Logo", "ROM cover successfully changed")

def deleteROM(rom_path):
    qm = QMessageBox
    ret = qm.question(window,'', "Are you sure you want to delete " + rom_path +" and rebuild the ROM list? " , qm.Yes | qm.No)
    if ret == qm.Yes:
        try:
            os.remove(rom_path)
            RunFrogTool()
            loadROMsToTable()
        except Exception:
            QMessageBox.about(window, "Error","Could not delete file.")
            loadROMsToTable()
        return
    else:
        return

def addToShortcuts(rom_path):
    qm = QMessageBox
    qm.setText("Time to set the rompath!")

def BGM_change(source=""):
    # Check the selected drive looks like a Frog card
    drive = window.combobox_drive.currentText()
    
    if not tadpole_functions.checkDriveLooksFroggy(drive):
        QMessageBox.about(window, "Something doesn't Look Right", "The selected drive doesn't contain critical \
        SF2000 files. The action you selected has been aborted for your safety.")
        return

    msg_box = QMessageBox()
    msg_box.setWindowTitle("Getting Background Music")
    msg_box.setText("Now getting background music. For downloads, this may take some time. Please wait patiently!")
    msg_box.show()

    if source[0:4] == "http":  # internet-based
        result = tadpole_functions.changeBackgroundMusic(drive, url=source)
    else:  # local resource
        result = tadpole_functions.changeBackgroundMusic(drive, file=source)

    if result:
        msg_box.close()
        QMessageBox.about(window, "Success", "Background music changed successfully")
    else:
        msg_box.close()
        QMessageBox.about(window, "Failure", "Something went wrong while trying to change the background music")


class BootLogoViewer(QLabel):
    """
    Args:
        parent (BootConfirmDialog): Parent widget. Used to enable/disable controls on parent.
        changeable (bool): If True, will allow importing new image. If False, will just allow static display.
    """
    def __init__(self, parent, changeable=False):
        super().__init__(parent)

        self.changeable = changeable
        self.path = ""  # Used to store path to the currently-displayed file

        self.setStyleSheet("background-color: white;")
        self.setMinimumSize(512, 200)  # resize to Froggy boot logo dimensions

        if self.changeable:
            self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.setText("Click to Select New Image")

    def mousePressEvent(self, ev):
        """
        Overrides built-in function to handle mouse click events. Prompts user for image path and loads same.
        """
        if self.changeable:  # only do something if image is changeable
            file_name = QFileDialog.getOpenFileName(self, 'Open file', '',
                                                    "Images (*.jpg *.png *.webp);;RAW (RGB565 Little Endian) Images (*.raw)")[0]
            if len(file_name) > 0:  # confirm if user selected a file
                self.load_image(file_name)

    def load_from_bios(self, drive: str):
        """
        Extracts image from the bios and passes to load image function.

        Args:
            drive (str):  Path to the root of the Froggy drive.
        """
        with open(os.path.join(drive, "bios", "bisrv.asd"), "rb") as bios_file:
            bios_content = bytearray(bios_file.read())

        offset = tadpole_functions.findSequence(tadpole_functions.offset_logo_presequence, bios_content) + 16
        with open(os.path.join(basedir, "bios_image.raw"), "wb") as image_file:
            image_file.write(bios_content[offset:offset+((512*200)*2)])

        self.load_image(os.path.join(basedir, "bios_image.raw"))

    def load_image(self, path: str) -> bool:
        """
        Loads an image into the viewer.  If the image is loaded successfully, may enable the parent Save button based
        on the changeable flag.

        Args:
            path (str): Path to the image.  Can be .raw or other format.  If .raw, assumed to be in RGB16 (RGB565 Little
                Endian) format used for Froggy boot logos.  Must be 512x200 pixels or it will not be accepted/displayed.

        Returns:
            bool: True if image was loaded, False if not.
        """
        if os.path.splitext(path)[1] == ".raw":  # if raw image, assume RGB16 (RGB565 Little Endian)
            with open(path, "rb") as f:
                img = QImage(f.read(), 512, 200, QImage.Format_RGB16)
        else:  # otherwise let QImage autodetection do its thing
            img = QImage(path)
            if (img.width(), img.height()) != (512, 200): 
                img = img.scaled(512, 200, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) #Rescale new boot logo to correct size
        self.path = path  # update path
        self.setPixmap(QPixmap().fromImage(img))

        if self.changeable:  # only enable saving for changeable dialogs; prevents enabling with load from bios
            self.parent().button_save.setDisabled(False)
        return True


class BootConfirmDialog(QDialog):
    """
    Dialog used to confirm boot logo selection with the ability to view existing selection and replacement.

    Args:
        drive (str): Path to root of froggy drive.
    """
    def __init__(self, drive):
        super().__init__()

        self.drive = drive

        self.setWindowTitle("Boot Image Selection")
        self.setWindowIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)))

        # Setup Main Layout
        self.layout_main = QVBoxLayout()
        self.setLayout(self.layout_main)

        # set up current image viewer
        self.layout_main.addWidget(QLabel("Current Image"))
        self.current_viewer = BootLogoViewer(self)
        self.layout_main.addWidget(self.current_viewer)

        self.layout_main.addWidget(QLabel(" "))  # spacer

        # set up new image viewer
        self.layout_main.addWidget(QLabel("New Image"))
        self.new_viewer = BootLogoViewer(self, changeable=True)
        self.layout_main.addWidget(self.new_viewer)

        # Main Buttons Layout (Save/Cancel)
        self.layout_buttons = QHBoxLayout()
        self.layout_main.addLayout(self.layout_buttons)

        # Save Button
        self.button_save = QPushButton("Save")
        self.button_save.setDefault(True)
        self.button_save.setDisabled(True)  # set disabled by default; need to wait for user to select new image
        self.button_save.clicked.connect(self.accept)
        self.layout_buttons.addWidget(self.button_save)

        # Cancel Button
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.reject)
        self.layout_buttons.addWidget(self.button_cancel)

        # Load Initial Image
        self.current_viewer.load_from_bios(self.drive)

class PleaseWaitDialog(QMainWindow):
    """
    Dialog used to stop interaction while something is happening from program root.
    """
    def __init__(self, message: str = ""):
        super().__init__()

        self.setWindowTitle("Please Wait")
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation))
        
        
        self.lbl = QLabel(self)
        #self.text_edit.setFixedSize(500, 500)
        self.setCentralWidget(self.lbl)
        self.lbl.setText(message)
        
    def setMessage(self, message: str = ""):
        self.lbl.setText(message)

class ReadmeDialog(QMainWindow):
    """
    Dialog used to display README.md file from program root.
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Read Me")
        self.setWindowIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarContextHelpButton))

        self.text_edit = QTextEdit(self)
        self.text_edit.setReadOnly(True)
        self.text_edit.setMinimumSize(500, 500)
        self.setCentralWidget(self.text_edit)
        try:
            with open(os.path.join(basedir, "README.md"), "r") as readme_file:
                self.text_edit.setMarkdown(readme_file.read())
        except FileNotFoundError:  # gracefully fail if file not present
            self.text_edit.setText(f"Unable to locate README.md file in program root folder {basedir}.")


class MusicConfirmDialog(QDialog):
    """Dialog used to confirm or load music selection with the ability to preview selection by listening to the music.
    If neither music_name nor music_url are provided, allows import from local file.

        Args:
            music_name (str) : Name of the music file; used only to show name in dialog
            music_url (str) : URL to a raw music file; should be formatted for use on SF2000 (raw signed 16-bit PCM,
                mono, little-endian, 22050 hz)
    """
    def __init__(self, music_name: str = "", music_url: str = ""):
        super().__init__()

        # Save Arguments
        self.music_name = music_name
        self.music_url = music_url
        self.music_file = ""  # used to store filename for local files

        # Configure Window
        self.setWindowTitle("Change Background Music")
        self.setWindowIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)))
        self.sound = QSoundEffect(self)  # Used to Play Music File

        # Setup Main Layout
        self.layout_main = QVBoxLayout()
        self.setLayout(self.layout_main)

        # Main Text
        self.label_confirm = QLabel("<h3>Change Background Music</h3><a href='#'>Select File</a>", self)
        if self.music_name == "" and self.music_url == "":
            self.label_confirm.linkActivated.connect(self.load_from_file)
            pass
        self.label_confirm.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.layout_main.addWidget(self.label_confirm)

        # Music Preview Button
        self.button_play = QPushButton(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)),
                                       " Preview",
                                       self)
        self.button_play.setDisabled(True)  # disable by default

        self.layout_main.addWidget(self.button_play)
        self.button_play.clicked.connect(self.toggle_audio)

        # Main Buttons Layout (Save/Cancel)
        self.layout_buttons = QHBoxLayout()
        self.layout_main.addLayout(self.layout_buttons)

        # Save Button
        self.button_save = QPushButton("Save")
        self.button_save.setDisabled(True)  # disable by default
        self.button_save.clicked.connect(self.accept)
        self.layout_buttons.addWidget(self.button_save)

        # Cancel Button
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.reject)
        self.layout_buttons.addWidget(self.button_cancel)

        if music_name and music_url:  # enable features only if using preset options
            self.label_confirm.setText("<h3>Change Background Music</h3><em>{}</em>".format(self.music_name))
            self.button_save.setEnabled(True)
            self.button_play.setEnabled(True)

    def toggle_audio(self) -> bool:
        """toggles music preview on or off

            Returns:
                bool: True if file is playing; false if not
        """
        if self.sound.isPlaying():
            self.sound.stop()
            self.button_play.setIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)))
            self.button_play.setText(" Preview")
            return False

        else:
            if not self.sound.source().path():  # fetch and convert raw file if not already done
                self.button_play.setDisabled(True)  # disable button while processing
                file_data = self.get_and_format_music_file()
                if file_data[0]:  # fetch/conversion succeeds
                    self.sound.setSource(QUrl.fromLocalFile(file_data[1]))
                    self.button_play.setEnabled(True)
                    self.button_save.setEnabled(True)  # enable saving as well since file seems OK
                else:  # fetch/conversion fails
                    self.button_play.setText(file_data[1])
                    self.button_play.setIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)))
                    return False

            # format button and play
            self.button_play.setIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop)))
            self.button_play.setText(" Stop")
            self.sound.setLoopCount(1000)
            self.sound.play()
            return True

    def get_and_format_music_file(self) -> (bool, str):
        """Downloads/loads and re-formats the raw music file as wav.

            Returns:
                tuple (bool, str): True or false based on success in fetching/converting file, and path to resulting
                    temporary wav file, error message if failed.
        """
        if self.music_url:  # handle internet downloads
            try:
                r = requests.get(self.music_url)
                if r.status_code == 200:  # download succeeds
                    raw_data = BytesIO(r.content)  # read raw file into memory
            except requests.exceptions.RequestException:  # catches exceptions for multiple reasons
                return False, "Download Failed"
        else:  # handle local files
            with open(self.music_file, "rb") as mf:
                raw_data = BytesIO(mf.read())

        wav_filename = os.path.join(basedir, "preview.wav")
        with wave.open(wav_filename, "wb") as wav_file:
            wav_file.setparams((1, 2, 22050, 0, 'NONE', 'NONE'))
            wav_file.writeframes(raw_data.read())
            if wav_file.getnframes() > (22050*90):  # check that file length does not exceed 90 seconds (max for Froggy)
                return False, "Duration Too Long (90s max)"
        return True, wav_filename

    def load_from_file(self) -> bool:
        file_name = QFileDialog.getOpenFileName(self, 'Open file', '',
                                                "Raw Signed 16-bit PCM - Mono, Little-Endian, 22050hz (*.*)")[0]
        if file_name:
            self.music_file = file_name
            self.music_name = os.path.split(file_name)[-1]
            self.label_confirm.setText("<h3>Change Background Music</h3><em>{}</em>".format(self.music_name))
            self.button_play.setEnabled(True)
            self.toggle_audio()
            return True
        return False


# SubClass QMainWindow to create a Tadpole general interface
class MainWindow (QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tadpole - SF2000 Tool")
        self.setWindowIcon(QIcon(os.path.join(basedir, 'frog.ico')))
        self.resize(1000,500)

        widget = QWidget()
        self.setCentralWidget(widget)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Load the Menus
        self.create_actions()
        self.loadMenus()

        # Create Layouts
        layout = QVBoxLayout(widget)
        selector_layout = QHBoxLayout()
        layout.addLayout(selector_layout)

        # Drive Select Widgets
        self.lbl_drive = QLabel(text="Drive:")
        self.lbl_drive.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.combobox_drive = QComboBox()
        self.combobox_drive.activated.connect(loadROMsToTable)
        self.btn_refreshDrives = QPushButton()
        self.btn_refreshDrives.setIcon(self.style().standardIcon(getattr(QStyle, "SP_BrowserReload")))
        self.btn_refreshDrives.clicked.connect(reloadDriveList)
        selector_layout.addWidget(self.lbl_drive)
        selector_layout.addWidget(self.combobox_drive, stretch=1)
        selector_layout.addWidget(self.btn_refreshDrives)

        # Spacer
        selector_layout.addWidget(QLabel(" "), stretch=2)

        # Console Select Widgets
        self.lbl_console = QLabel(text="Console:")
        self.lbl_console.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.combobox_console = QComboBox()
        self.combobox_console.activated.connect(loadROMsToTable)
        selector_layout.addWidget(self.lbl_console)
        selector_layout.addWidget(self.combobox_console, stretch=1)
        
        # Update Button Widget
        self.btn_update = QPushButton("Rebuild!")
        selector_layout.addWidget(self.btn_update)
        self.btn_update.clicked.connect(RunFrogTool)

        # Game Table Widget
        self.tbl_gamelist = QTableWidget()
        self.tbl_gamelist.setColumnCount(5)
        self.tbl_gamelist.setHorizontalHeaderLabels(["Name", "Size", "Thumbnail", "Delete ROM", "Shortcut Slot"])
        self.tbl_gamelist.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_gamelist.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_gamelist.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_gamelist.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tbl_gamelist.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.tbl_gamelist.cellClicked.connect(catchTableCellClicked)
        layout.addWidget(self.tbl_gamelist)

        self.readme_dialog = ReadmeDialog()

        # Reload Drives Timer
        self.timer = QTimer()
        self.timer.timeout.connect(reloadDriveList)
        self.timer.start(1000)

    
    def create_actions(self):
        # File Menu
        self.about_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation),
                                    "&About",
                                    self,
                                    triggered=self.about)
        self.exit_action = QAction("E&xit", self, shortcut="Ctrl+Q",triggered=self.close)

    def loadMenus(self):
        self.menu_file = self.menuBar().addMenu("&File")
        self.menu_file.addAction(self.exit_action)
        #self.action_Test = QAction("Test Function", self,triggered=self.testFunction)
        #self.menu_file.addAction(self.action_Test)
        
        # OS Menu
        self.menu_os = self.menuBar().addMenu("&OS")
        # Update Submenu
        action_detectOSVersion = QAction("Detect and update firmware", self, triggered=self.detectOSVersion)
        self.menu_os.addAction(action_detectOSVersion)
        self.menu_os.menu_update = self.menu_os.addMenu("Manually change firmware")
        action_updateTo20230803  = QAction("2023.08.03 (V1.6)", self, triggered=self.Updateto20230803)                                                                              
        self.menu_os.menu_update.addAction(action_updateTo20230803)   
        self.action_updateToV1_5  = QAction("2023.04.20 (V1.5)", self, triggered=self.UpdatetoV1_5)                                                                              
        self.menu_os.menu_update.addAction(self.action_updateToV1_5)   
        self.action_changeBootLogo  = QAction("Change &Boot Logo", self, triggered=self.changeBootLogo)
        self.menu_os.addAction(self.action_changeBootLogo)
        # Console Logos Submenu
        self.menu_consoleLogos = self.menu_os.addMenu("Console Logos")
        self.action_consolelogos_Default = QAction("Restore Default", self, triggered=self.ConsoleLogos_RestoreDefault)
        self.menu_consoleLogos.addAction(self.action_consolelogos_Default)
        self.action_consolelogos_Western = QAction("Western Logos", self, triggered=self.ConsoleLogos_WesternLogos)
        self.menu_consoleLogos.addAction(self.action_consolelogos_Western)
        self.GBABIOSFix_action = QAction("&GBA BIOS Fix", self, triggered=self.GBABIOSFix)
        self.menu_os.addAction(self.GBABIOSFix_action)
        self.action_changeShortcuts = QAction("Change Game Shortcuts", self, triggered=self.changeGameShortcuts)
        self.menu_os.addAction(self.action_changeShortcuts)
        self.action_removeShortcutLabels = QAction("Remove Shortcut Labels", self, triggered=self.removeShortcutLabels)
        self.menu_os.addAction(self.action_removeShortcutLabels)

        # Background Music Menu
        self.menu_bgm = self.menuBar().addMenu("&Background Music")
        try:
            self.music_options = tadpole_functions.get_background_music()
        except (ConnectionError, requests.exceptions.ConnectionError):
            self.status_bar.showMessage("Error loading external music resources.", 20000)
            error_action = QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)),
                                   "Error Loading External Resources!",
                                   self)
            error_action.setDisabled(True)
            self.menu_bgm.addAction(error_action)
        else:
            for music in self.music_options:
                self.menu_bgm.addAction(QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume)),
                                                music,
                                                self,
                                                triggered=self.change_background_music))
        self.menu_bgm.addSeparator()
        self.menu_bgm.addAction(QAction(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogOpenButton)),
                                        "From Local File...",
                                        self,
                                        triggered=self.change_background_music))

        # Download Thumbnails Menu
        self.menu_boxart = self.menuBar().addMenu("Thumbnails")
        self.DownloadBoxart_action = QAction("Download Boxart thumbnails for zip files", self, triggered=self.downloadBoxartForZips)
        self.menu_boxart.addAction(self.DownloadBoxart_action)
        self.DownloadBoxart_action = QAction("Download Snaps thumbnails for zip files", self, triggered=self.downloadBoxartForZips)
        self.menu_boxart.addAction(self.DownloadBoxart_action)
        self.DownloadBoxart_action = QAction("Download Titles thumbnails for zip files", self, triggered=self.downloadBoxartForZips)
        self.menu_boxart.addAction(self.DownloadBoxart_action)

        # Saves Menu
        self.menu_roms = self.menuBar().addMenu("ROMs")
        BackupAllSaves_action = QAction("Backup All ROMs saves", self, triggered=self.createSaveBackup)
        self.menu_roms.addAction(BackupAllSaves_action)
        CopyRoms_action = QAction("Add (Copy) ROMs...", self, triggered=self.copyRoms)
        self.menu_roms.addAction(CopyRoms_action)
        
        # Help Menu
        self.menu_help = self.menuBar().addMenu("&Help")
        self.readme_action = QAction(self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarContextHelpButton),
                                     "Read Me",
                                     triggered=self.show_readme)
        self.menu_help.addAction(self.readme_action)
        self.menu_help.addSeparator()
        self.menu_help.addAction(self.about_action)

    def testFunction(self):
        print("Called test function. Remember to disable this before publishing")
        try:
            tadpole_functions.bisrv_getFirmwareVersion("C:\\Users\\OEM\\Downloads\\bisrv (1).asd")
        except tadpole_functions.InvalidURLError:
            print("URL did not return a valid file")
    
    def detectOSVersion(self):
        print("Tadpole~DetectOSVersion: Trying to read bisrv hash")
        drive = window.combobox_drive.currentText()
        msg_box = DownloadMessageBox()
        msg_box.setText("Detecting firmware version")
        msg_box.show()
        try:
            msg_box.showProgress(50)
            detectedVersion = tadpole_functions.bisrv_getFirmwareVersion(os.path.join(drive,"bios","bisrv.asd"))
            if not detectedVersion:
                detectedVersion = "Version Not Found"
            #TODO: move this from string base to something else...or at lesat make sure this gets updated when/if new firmware gets out there
            if detectedVersion != "2023.08.03 (V1.6)":
                qm = QMessageBox
                ret = qm.question(self,"Detected OS Version", f"Detected version: "+ detectedVersion + "\nDo you want to update to the latest firmware?" , qm.Yes | qm.No)
                if ret == qm.Yes:
                    MainWindow.Updateto20230803(self)
                else:
                    return
            else:
                QMessageBox.about(self, "Detected OS Version", f"You are on the latest firmware: {detectedVersion}")

        except Exception as e:
            QMessageBox.about("tadpole~detectOSVersion: Error occured while trying to find OS Version" + str(e))
    
    def downloadBoxartForZips(self):
        drive = window.combobox_drive.currentText()
        user_selected_console = window.combobox_console.currentText()
        #ARCADE can't get ROM art, so just return
        if user_selected_console == "ARCADE":
            QMessageBox.about(self, "Download Thumbnails", "Custom Arcade ROMs cannot have thumbnails at this time.")
            return
        
        msgBox = DownloadMessageBox()
        msgBox.setText("Downloading thumbnails...")

        #TODO hook up a cancel button...but I can't get it to work right now
        #cancelBtn = msgBox.addButton('Cancel', QMessageBox.RejectRole)
        #layout.addWidget(cancelBtn,layout.rowCount(), 0, 1, layout.columnCount(), Qt.AlignCenter )

        msgBox.show()

        #Need the url for scraping the png's, which is different
        ROMART_baseURL_parsing = "https://github.com/EricGoldsteinNz/libretro-thumbnails/tree/master/"
        
        ROMArt_console = {  
            "FC":     "Nintendo - Nintendo Entertainment System",
            "SFC":    "Nintendo - Super Nintendo Entertainment System",
            "MD":     "Sega - Mega Drive - Genesis",
            "GB":     "Nintendo - Game Boy",
            "GBC":    "Nintendo - Game Boy Color",
            "GBA":    "Nintendo - Game Boy Advance", 
            "ARCADE": ""
        }

        #TODO: I shouldn't base this on strings incase it gets localized, should base it on the item clicked with "sender" obj but I can't figure out where that data is in that object 
        art_Selection = self.sender().text()
        if('Titles' in art_Selection):
            art_Type = "/Named_Titles/"
        elif('Snaps'in art_Selection):
            art_Type = "/Named_Snaps/"
        else:
           art_Type = "/Named_Boxarts/"
        counter_success = 0
        counter_total = 0
        #TODO: this needs to be cleaned up and turned into a tadpole_function
        if user_selected_console == "ALL":
            for console in tadpole_functions.systems.keys():
                if console == "ARCADE":
                    continue
                zip_files = os.scandir(os.path.join(drive,console))
                zip_files = list(filter(frogtool.check_zip, zip_files))
                msgBox.setText("Trying to find thumbnails for " + str(len(zip_files)) + " ROMs\n" + ROMArt_console[console])
                #reset progress bar for next console
                games_total = 0
                msgBox.progress.reset()
                msgBox.progress.setMaximum(len(zip_files)+1)
                msgBox.progress.setValue(0)
                QApplication.processEvents()
                #Scrape the url for .png files
                url_for_scraping = ROMART_baseURL_parsing + ROMArt_console[console] + art_Type
                response = requests.get(url_for_scraping)
                # BeautifulSoup magically find ours PNG's and ties them up into a nice bow
                soup = BeautifulSoup(response.content, 'html.parser')
                json_response = json.loads(soup.contents[0])
                png_files = []
                for value in json_response['payload']['tree']['items']:
                    png_files.append(value['name'])

                for file in zip_files:
                    game = os.path.splitext(file.name)
                    outFile = os.path.join(os.path.dirname(file.path),f"{game[0]}.png")
                    games_total = games_total +1
                    msgBox.progress.setValue(games_total)
                    QApplication.processEvents()
                    if not os.path.exists(outFile):
                        counter_total = counter_total + 1
                        url_to_download = ROMART_baseURL_parsing + ROMArt_console[console] + art_Type + game[0]
                        for x in png_files:
                            if game[0] in x:
                                tadpole_functions.downloadROMArt(console,file.path,x,art_Type,game[0])
                                counter_success = counter_success + 1
                                break
        else:
            console = user_selected_console
            zip_files = os.scandir(os.path.join(drive,console))
            zip_files = list(filter(frogtool.check_zip, zip_files))
            msgBox.setText("Trying to find thumbnails for " + str(len(zip_files)) + " ROMs\n" + ROMArt_console[console])
            #reset progress bar for next console
            games_total = 0
            msgBox.progress.reset()
            msgBox.progress.setMaximum(len(zip_files)+1)
            msgBox.progress.setValue(0)
            QApplication.processEvents()
            #Scrape the url for .png files
            url_for_scraping = ROMART_baseURL_parsing + ROMArt_console[console] + art_Type
            response = requests.get(url_for_scraping)
            # BeautifulSoup magically find ours PNG's and ties them up into a nice bow
            soup = BeautifulSoup(response.content, 'html.parser')
            json_response = json.loads(soup.contents[0])
            png_files = []
            for value in json_response['payload']['tree']['items']:
                png_files.append(value['name'])

            for file in zip_files:
                game = os.path.splitext(file.name)
                outFile = os.path.join(os.path.dirname(file.path),f"{game[0]}.png")
                games_total = games_total +1
                msgBox.progress.setValue(games_total)
                QApplication.processEvents()
                if not os.path.exists(outFile):
                    counter_total = counter_total + 1
                    url_to_download = ROMART_baseURL_parsing + ROMArt_console[console] + art_Type + game[0]
                    for x in png_files:
                        if game[0] in x:
                            tadpole_functions.downloadROMArt(console,file.path,x,art_Type,game[0])
                            counter_success = counter_success + 1
                            break
        QApplication.processEvents()

        qm = QMessageBox
        ret = qm.question(self,'', "Downloading Boxart Complete\n" + f"Found {counter_success} covers for {counter_total} zips for {console}.\n\nDo you want to rebuild game lists?", qm.Yes | qm.No)
        if ret == qm.Yes:
            RunFrogTool()
            return
        else:
            return


    def change_background_music(self):
        """event to change background music"""
        if self.sender().text() == "From Local File...":  # handle local file option
            d = MusicConfirmDialog()
            local = True
        else:  # handle preset options
            d = MusicConfirmDialog(self.sender().text(), self.music_options[self.sender().text()])
            local = False
        if d.exec():
            if local:
                BGM_change(d.music_file)
            else:
                BGM_change(self.music_options[self.sender().text()])

    def about(self):
        QMessageBox.about(self, "About Tadpole", 
                                "Tadpole was created by EricGoldstein based on the original work \
from tzlion on frogtool. Special thanks also goes to wikkiewikkie for many amazing improvements")

    def GBABIOSFix(self):
        drive = window.combobox_drive.currentText()
        try:
            tadpole_functions.GBABIOSFix(drive)
        except tadpole_functions.Exception_InvalidPath:
            QMessageBox.about(self, "GBA BIOS Fix", "An error occurred. Please ensure that you have the right drive \
            selected and <i>gba_bios.bin</i> exists in the <i>bios</i> folder")
            return
        QMessageBox.about(self, "GBA BIOS Fix", "BIOS successfully copied")
        
    def changeBootLogo(self):
        dialog = BootConfirmDialog(window.combobox_drive.currentText())
        change = dialog.exec()
        if change:
            newLogoFileName = dialog.new_viewer.path
            print(f"user tried to load image: {newLogoFileName}")
            if newLogoFileName is None or newLogoFileName == "":
                print("user cancelled image select")
                return

            try:
                tadpole_functions.changeBootLogo(os.path.join(window.combobox_drive.currentText(),
                                                              "bios",
                                                              "bisrv.asd"),
                                                 newLogoFileName)
            except tadpole_functions.Exception_InvalidPath:
                QMessageBox.about(self, "Change Boot Logo", "An error occurred. Please ensure that you have the right \
                drive selected and <i>bisrv.asd</i> exists in the <i>bios</i> folder")
                return
            QMessageBox.about(self, "Change Boot Logo", "Boot logo successfully changed")
      
    def changeGameShortcuts(self):
        drive = window.combobox_drive.currentText()
        # Check the selected drive looks like a Frog card
        
        # Open a new modal to change the shortcuts for a specific gamename
        window.window_shortcuts = changeGameShortcutsWindow()
        window.window_shortcuts.setDrive(drive)
        window.window_shortcuts.show()
    
    def removeShortcutLabels(self):
        drive = window.combobox_drive.currentText()
        if tadpole_functions.stripShortcutText(drive):
            QMessageBox.about(window, "Successfully removed Shortcut Labels", "Success!.")
        else:
            QMessageBox.about(window, "Something went wrong", "An error occured. Please contact EricGoldstein via the RetroHandheld Discord to look into it.")
        #self.UnderDevelopmentPopup()
        
    def ConsoleLogos_RestoreDefault(self):
        self.ConsoleLogos_change("https://github.com/EricGoldsteinNz/SF2000_Resources/raw/main/ConsoleLogos/default/sfcdr.cpl")
    
    def ConsoleLogos_WesternLogos(self):
        self.ConsoleLogos_change("https://github.com/EricGoldsteinNz/SF2000_Resources/raw/main/ConsoleLogos/western_console_logos/sfcdr.cpl")

    def UnderDevelopmentPopup(self):
        QMessageBox.about(self, "Development", "This feature is still under development")
        
    def ConsoleLogos_change(self, url):
        drive = window.combobox_drive.currentText()
        
        if not tadpole_functions.checkDriveLooksFroggy(drive):
            QMessageBox.about(window, "Something doesn't Look Right", "The selected drive doesn't contain critical \
            SF2000 files. The action you selected has been aborted for your safety.")
            return
        
        msgBox = DownloadMessageBox()
        msgBox.setText(" Downloading Console logos.")
        msgBox.show()
        msgBox.showProgress(25)
        if tadpole_functions.changeConsoleLogos(drive, url):
            msgBox.close()
            QMessageBox.about(self, "Success", "Console logos successfully changed")
        else:
            msgBox.close()
            QMessageBox.about(self, "Failure", "ERROR: Something went wrong while trying to change the console logos")

    def show_readme(self):
        self.readme_dialog.show()

    def UpdatetoV1_5(self):
        url = "https://api.github.com/repos/EricGoldsteinNz/SF2000_Resources/contents/OS/V1.5"
        self.UpdateDevice(url)
    
    def Updateto20230803(self):
        url = "https://api.github.com/repos/EricGoldsteinNz/SF2000_Resources/contents/OS/20230803"
        self.UpdateDevice(url)

    def UpdateDevice(self, url):
        drive = window.combobox_drive.currentText()
        msgBox = DownloadMessageBox()
        msgBox.setText("Downloading Firmware Update.")
        msgBox.show()
        msgBox.showProgress(25)

        if tadpole_functions.downloadDirectoryFromGithub(drive, url):
            msgBox.close()
            QMessageBox.about(self, "Success","Update successfully Downloaded")
        else:
            msgBox.close()
            QMessageBox.about(self, "Failure","ERROR: Something went wrong while trying to download the update")
            
    def createSaveBackup(self):
        drive = window.combobox_drive.currentText()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Creating Save Backup")
        msgBox.setText("Please Wait")
        msgBox.show()
        savefilename = f"SF2000SaveBackup_{timestamp}.zip"
        if tadpole_functions.createSaveBackup(drive,savefilename):   
            msgBox.close()
            QMessageBox.about(self, "Success",f"Save backup created as:\n\r{savefilename}")
        else:
            msgBox.close()
            QMessageBox.about(self, "Failure","ERROR: Something went wrong while trying to create the save backup")    
        
    def copyRoms(self):
        drive = window.combobox_drive.currentText()
        console = window.combobox_console.currentText()

        if(console == "ALL"):
            QMessageBox.about(self, "Action needed",f"Please select a console in the dropdown")
            return
        filenames, _ = QFileDialog.getOpenFileNames(self,"Select ROMs",'',"ROM files (*.zip *.bkp \
                                                    *.zfc *.zsf *.zmd *.zgb *.zfb *.smc *.fig *.sfc *.gd3 *.gd7 *.dx2 *.bsx *.swc \
                                                    *.nes *.nfc *.fds *.unf *.gbc *.gb *.sgb *.gba *.agb *.gbz *.bin *.md *.smd *.gen *.sms)")
        if filenames:
            for filename in filenames:
                shutil.copy(filename, drive + console)
                print (filename + "added to " + drive + console)
            qm = QMessageBox
            ret = qm.question(self,'', f"Added " + str(len(filenames)) + " ROMs to " + drive + console + "\n\nDo you want to try to download thumbnails?", qm.Yes | qm.No)
            if ret == qm.Yes:
                MainWindow.downloadBoxartForZips(self)
                loadROMsToTable()
                return
            else:
                loadROMsToTable()
                return
    def validateGameShortcutComboBox(self):
        currentComboBox = self.sender() 
        if currentComboBox.currentText() != '':
            for i in range(self.tbl_gamelist.rowCount()):
                comboBox = window.tbl_gamelist.cellWidget(i, 4)
                if comboBox == currentComboBox:
                    continue
                if comboBox.currentText() == currentComboBox.currentText():
                    QMessageBox.about(window, "Error","You had the shortcut: " + comboBox.currentText() + " assigned to " + window.tbl_gamelist.item(i, 0).text()+ "\nChanging it to the newly selected game.")
                    comboBox.setCurrentIndex(0)
                    return False
        return True

# Subclass Qidget to create a thumbnail viewing window        
class thumbnailWindow(QDialog):
    """
        This window should be called without a parent widget so that it is created in its own window.
    """
    def __init__(self, filepath):
        super().__init__()
        layout = QVBoxLayout()
        
        self.setWindowIcon(QIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)))
        self.setWindowTitle(f"Thumbnail - {filepath}")
        
        # Setup Main Layout
        self.layout_main = QVBoxLayout()
        self.setLayout(self.layout_main)

        # set up current image viewer
        self.layout_main.addWidget(QLabel("Current Image"))
        self.current_viewer = ROMCoverViewer(self)
        self.layout_main.addWidget(self.current_viewer, Qt.AlignCenter)

        self.layout_main.addWidget(QLabel(" "))  # spacer

        # set up new image viewer
        self.layout_main.addWidget(QLabel("New Image"))
        self.new_viewer = ROMCoverViewer(self, changeable=True)
        self.layout_main.addWidget(self.new_viewer, Qt.AlignCenter)

        # Main Buttons Layout (Save/Cancel)
        self.layout_buttons = QHBoxLayout()
        self.layout_main.addLayout(self.layout_buttons)
        
        #Save Existing Cover To File Button
        self.button_write = QPushButton("Save Existing to File")
        self.button_write.clicked.connect(self.WriteImgToFile)
        self.layout_buttons.addWidget(self.button_write)     

        # Save Button
        self.button_save = QPushButton("Overwrite Cover")
        self.button_save.setDefault(True)
        self.button_save.setDisabled(True)  # set disabled by default; need to wait for user to select new image
        self.button_save.clicked.connect(self.accept)
        self.layout_buttons.addWidget(self.button_save)

        # Cancel Button
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.reject)
        self.layout_buttons.addWidget(self.button_cancel)

        # Load Initial Image
        self.current_viewer.load_from_ROM(filepath)
        
    def WriteImgToFile(self):
        newCoverFileName = QFileDialog.getSaveFileName(window,
                                                       'Save Cover',
                                                       'c:\\',
                                                       "Image files (*.png)")[0]
        
        if newCoverFileName is None or newCoverFileName == "":
            print("user cancelled save select")
            return      
        try:
            tadpole_functions.extractImgFromROM(self.current_viewer.path, newCoverFileName)
        except tadpole_functions.Exception_InvalidPath:
            QMessageBox.about(window, "Save ROM Cover", "An error occurred.")
            return
        QMessageBox.about(window, "Save ROM Cover", "ROM cover successfully")
       


class ROMCoverViewer(QLabel):
    """
    Args:
        parent (thumbnailWindow): Parent widget. Used to enable/disable controls on parent.
        changeable (bool): If True, will allow importing new image. If False, will just allow static display.
    """
    def __init__(self, parent, changeable=False):
        super().__init__(parent)

        self.changeable = changeable
        self.path = ""  # Used to store path to the currently-displayed file

        self.setStyleSheet("background-color: white;")
        self.setMinimumSize(144, 208)  # resize to Froggy ROM logo dimensions
        self.setFixedSize(144, 208)  # resize to Froggy ROM logo dimensions

        if self.changeable:
            self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            self.setText("Click to Select New Image")

    def mousePressEvent(self, ev):
        """
        Overrides built-in function to handle mouse click events. Prompts user for image path and loads same.
        """
        if self.changeable:  # only do something if image is changeable
            file_name = QFileDialog.getOpenFileName(self, 'Open file', '',
                                                    "Image files (*.gif *jpeg *.jpg *.png *.webp);;All Files (*.*)")[0]
            if len(file_name) > 0:  # confirm if user selected a file
                self.load_image(file_name)

    def load_from_ROM(self, pathToROM: str):
        """
        Extracts image from the bios and passes to load image function.

        Args:
            drive (str):  Path to the root of the Froggy drive.
        """
        print(f"loading cover from {pathToROM}")
        with open(pathToROM, "rb") as rom_file:
            rom_content = bytearray(rom_file.read())
        with open(os.path.join(basedir, "temp_rom_cover.raw"), "wb") as image_file:
            image_file.write(rom_content[0:((144*208)*2)])

        self.load_image(os.path.join(basedir, "temp_rom_cover.raw"))

    def load_image(self, path: str) -> bool:
        """
        Loads an image into the viewer.  If the image is loaded successfully, may enable the parent Save button based
        on the changeable flag.

        Args:
            path (str): Path to the image.  Can be .raw or other format.  If .raw, assumed to be in RGB16 (RGB565 Little
                Endian) format used for Froggy boot logos.  Must be 512x200 pixels or it will not be accepted/displayed.

        Returns:
            bool: True if image was loaded, False if not.
        """
        if os.path.splitext(path)[1] == ".raw":  # if raw image, assume RGB16 (RGB565 Little Endian)
            with open(path, "rb") as f:
                img = QImage(f.read(), 144, 208, QImage.Format_RGB16)
        else:  # otherwise let QImage autodetection do its thing
            img = QImage(path)
            if (img.width(), img.height()) != (144, 208): 
                img = img.scaled(144, 208, Qt.IgnoreAspectRatio, Qt.SmoothTransformation) #Rescale new boot logo to correct size
        self.path = path  # update path
        self.setPixmap(QPixmap().fromImage(img))

        if self.changeable:  # only enable saving for changeable dialogs; prevents enabling with load from bios
            self.parent().button_save.setDisabled(False)
        return True

class DownloadMessageBox(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        grid_layout = self.layout()

        qt_msgboxex_icon_label = self.findChild(QLabel, "qt_msgboxex_icon_label")
        qt_msgboxex_icon_label.deleteLater()

        qt_msgbox_label = self.findChild(QLabel, "qt_msgbox_label")
        qt_msgbox_label.setAlignment(Qt.AlignCenter)
        grid_layout.removeWidget(qt_msgbox_label)

        qt_msgbox_buttonbox = self.findChild(QDialogButtonBox, "qt_msgbox_buttonbox")
        grid_layout.removeWidget(qt_msgbox_buttonbox)
        
        self.setStyleSheet("QLabel{min-width: 300px}")
        self.setWindowFlags(Qt.CustomizeWindowHint)
        self.setSizePolicy(QSizePolicy.Expanding,QSizePolicy.Expanding)
        # Create a dialog for progress
        self.progress = QProgressBar()
        self.progress.setFixedWidth(300)

        self.spacer = QSpacerItem(0, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        grid_layout.addItem(self.spacer, 0, 0, 1, self.layout().columnCount())
        grid_layout.addWidget(qt_msgbox_label, 1, 0, alignment=Qt.AlignCenter)
        # Add the progress bar at the bottom (last row + 1) and first column with column span
        grid_layout.addWidget(self.progress,2, 0, 1, grid_layout.columnCount(), Qt.AlignCenter )
        grid_layout.addWidget(qt_msgbox_buttonbox, 3, 0, alignment=Qt.AlignCenter)
        qt_msgbox_buttonbox.hide()
    
    def setText(self, text):
        super().setText(text)
        
        longest = ""
        for part in text.split("\n"):
            if len(part) > len(longest):
                longest = part
        
        font_matrix = self.fontMetrics()
        width = font_matrix.boundingRect(longest).width() + 8 # Have to add ~20 as a buffer
        self.spacer = QSpacerItem(width, 0, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout().addItem(self.spacer, 0, 0, 1, self.layout().columnCount())
        
    def showProgress(self, progressValue):
        start_time = time.time()
        self.progress.setValue(progressValue)
        QApplication.processEvents()
        
        #qt_msgbox_label = self.findChild(QLabel, "qt_msgbox_label")
        #print(f"Width: {qt_msgbox_label.width()}")
        #self.setFixedWidth(qt_msgbox_label.width()+100)


# Subclass Qidget to create a change shortcut window        
class changeGameShortcutsWindow(QWidget):
    """
        This window should be called without a parent widget so that it is created in its own window.
    """
    drive = ""
   
    def __init__(self):
        super().__init__()

        layout = QHBoxLayout()
        # Console select
        self.combobox_console = QComboBox()
        
        layout.addWidget(QLabel("Console:"))
        layout.addWidget(self.combobox_console)

        # Position select
        self.combobox_shortcut = QComboBox()
        layout.addWidget(QLabel("Shortcut:"))
        layout.addWidget(self.combobox_shortcut)

        # Game Select
        self.combobox_games = QComboBox()
        layout.addWidget(QLabel("Game:"))
        layout.addWidget(self.combobox_games, stretch=1)

        # Update Button Widget
        self.btn_update = QPushButton("Update!")
        layout.addWidget(self.btn_update)
        self.btn_update.clicked.connect(self.changeShortcut) 

        self.setLayout(layout)
        self.setWindowTitle(f"Change System Shortcuts") 
        for console in frogtool.systems.keys():
            self.combobox_console.addItem(QIcon(), console, console)
        
        for i in range(1, 5):
            self.combobox_shortcut.addItem(QIcon(), f"{i}", i)
        self.combobox_console.currentIndexChanged.connect(self.loadROMsToGameShortcutList) 

    def setDrive(self,drive):
        self.drive = drive
        self.setWindowTitle(f"Change System Shortcuts - {drive}") 
    
    def loadROMsToGameShortcutList(self,index):
        print("reloading shortcut game table")
        #TODO
        if self.drive == "":
            print("ERROR: tried to load games for shortcuts on a blank drive")
            return
        system = self.combobox_console.currentText()
        if system == "" or system == "???":
            print("ERROR: tried to load games for shortcuts on an incorrect system")
            return
        roms_path = os.path.join(self.drive, system)
        try:
            files = frogtool.getROMList(roms_path)
            self.combobox_games.clear()
            for file in files:
                self.combobox_games.addItem(QIcon(),file,file)
            # window.window_shortcuts.combobox_games.adjustSize()
        except frogtool.StopExecution:
            # Empty the table
            window.tbl_gamelist.setRowCount(0)
            
    def changeShortcut(self):
        console = self.combobox_console.currentText()
        position = int(self.combobox_shortcut.currentText()) - 1 
        game = self.combobox_games.currentText()
        if console == "" or position == "" or game == "":
            print("ERROR: There was an error due to one of the shortcut parameters being blank!")
            QMessageBox.about(self, "ERROR", "One of the shortcut parameters was blank. That's not allowed for your \
            safety.")
            return
        tadpole_functions.changeGameShortcut(f"{self.drive}", console, position,game)
        print(f"changed {console} shortcut {position} to {game} successfully")
        QMessageBox.about(window, "Success", f"changed {console} shortcut {position} to {game} successfully")
        

if __name__ == "__main__":
    # Initialise the Application
    app = QApplication(sys.argv)

    # Build the Window
    window = MainWindow()

    # Update list of drives
    window.combobox_drive.addItem(QIcon(), static_NoDrives, static_NoDrives)
    reloadDriveList()

    # Update list of consoles
    available_consoles_placeholder = "???"
    window.combobox_console.addItem(QIcon(), available_consoles_placeholder, available_consoles_placeholder)
    window.combobox_console.clear()
    # Add ALL to the list to add this fucntionality from frogtool
    window.combobox_console.addItem(QIcon(), static_AllSystems, static_AllSystems)
    for console in tadpole_functions.systems.keys():
        window.combobox_console.addItem(QIcon(), console, console)
    
    window.show()
    app.exec()
