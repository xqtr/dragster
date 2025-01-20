#!/usr/bin/python3


"""
Dragster - Drag'n'drop utility to quick access functions on your system
==============================================================

It's a small program to drag stuff from your desktop/applications and make
quick actions, with the info dropped, like save them to a file, open another
program, backup etc.

You place it on your desktop and start dragging things. Select actions with right click

Features:
- You can add your own custom actions
- You can have multiple instances of the program, with different settings and actions
- Multiple tags to add, to create many actions
- Customizable appearance, size, color, transparency, position.

TIP:
To resize, press ALT and drag with RIGHT mouse button
To move, press ALT and drag with LEFT mouse button

Requirements:
- Python 3.6+
- PyQt5 libs

Author: XQTR // https://github.com/xqtr // https://cp737.net
License: GPL-3.0+
Version: 1.0.0
"""

import sys,os
from PyQt5.QtWidgets import QApplication, QMainWindow, QTextEdit, QMenu, QAction, QMessageBox
from PyQt5.QtCore import Qt
from PyQt5 import QtGui
import json
import argparse
from urllib.parse import unquote
from datetime import datetime

SETTINGS={}
ACTIONS=[]
DIR = os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), '')

def is_dark_mode():
    # Check the GTK theme settings
    setting = os.popen("gsettings get org.gnome.desktop.interface color-scheme").read().strip()
    return 'dark' in setting

class CustomTextEdit(QTextEdit):
    """Custom QTextEdit to override the default context menu."""
    def __init__(self, parent):
        super().__init__(parent)

    def contextMenuEvent(self, event):
        # Call the parent window's context menu
        self.parent().contextMenuEvent(event)

class DragDropWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        global SETTINGS
        # Set up the main window as frameless and transparent
        self.setWindowIcon(QtGui.QIcon('dragster.png'))
        self.setWindowTitle("Dragster")
        self.setGeometry(SETTINGS.get('x'), SETTINGS.get('y'), SETTINGS.get('width'), SETTINGS.get('height'))
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)


        # Create a custom text edit widget for displaying dropped content
        self.textEdit = CustomTextEdit(self)
        self.textEdit.setReadOnly(True)
        self.textEdit.setStyleSheet(f"""
                QTextEdit {{
                    background: rgba({SETTINGS.get('background')});
                    border: none;
                    color: {SETTINGS.get('textcolor')};
                    font-size: {SETTINGS.get('fontsize')}px;
                    padding: {SETTINGS.get('padding')}px;
                    border-radius: {SETTINGS.get('radius')}px;
                }}
                QScrollBar:vertical, QScrollBar:horizontal {{
                  background: transparent;
                  color: {SETTINGS.get('scroll_color')};
                  width: {SETTINGS.get('scroll_width')}px;
                }}
            """)
        self.setCentralWidget(self.textEdit)

        # Enable drag and drop
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        # Accept drag event if it contains URLs or text
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        # Handle drop event
        if event.mimeData().hasUrls():
            items = [url.toString() for url in event.mimeData().urls()]
        elif event.mimeData().hasText():
            items = [event.mimeData().text()]
        else:
            items = []

        if items:
            self.displayItems(items)
        #    self.showPopupMenu(items, event.pos())

    def displayItems(self, items):
        # Display the dropped items in the text area
        for item in items:
            self.textEdit.append(item)

    def showPopupMenu(self, items, pos):
        # Create a popup menu for dropped items
        menu = QMenu(self)

        # Define menu actions
        action1 = QAction("Show Details", self)
        action1.triggered.connect(lambda: self.showDetails(items))

        action2 = QAction("Clear Window", self)
        action2.triggered.connect(self.clearWindow)

        action3 = QAction("Do Nothing", self)

        # Add actions to the menu
        menu.addAction(action1)
        menu.addAction(action2)
        menu.addSeparator()
        menu.addAction(action3)

        # Display the menu at the mouse position
        global_pos = self.mapToGlobal(pos)
        menu.exec_(global_pos)

    def contextMenuEvent(self, event):
        global ACTIONS
        # Handle right-click context menu
        menu = QMenu(self)
        
        for action in ACTIONS:
            #print(action)
            actentry = QAction(action['name'], self)
            if action.get('type') == 'text':
                actentry.triggered.connect(lambda checked, arg=action.get('command'): self.textaction(arg))
                menu.addAction(actentry)
            elif action.get('type') == 'url':
                actentry.triggered.connect(lambda checked, arg=action.get('command'): self.urlaction(arg))
                menu.addAction(actentry)
            elif action.get('type') == 'file':
                actentry.triggered.connect(lambda checked, arg=action.get('command'): self.fileaction(arg))
                menu.addAction(actentry)
            elif action.get('type') == 'separator':
                menu.addSeparator()

        # Define actions
        action_close = QAction("Close App", self)
        action_close.triggered.connect(self.close)

        action_settings = QAction("Settings", self)
        action_settings.triggered.connect(self.openSettings)
        
        action_clear = QAction("Clear Text", self)
        action_clear.triggered.connect(self.clearWindow)

        action_about = QAction("About", self)
        action_about.triggered.connect(self.showAbout)
        
        # Add actions to the menu
        menu.addSeparator()
        menu.addAction(action_clear)
        menu.addAction(action_close)
        #menu.addAction(action_settings)
        #menu.addAction(action_about)

        # Show the menu
        menu.exec_(event.globalPos())

    def textaction(self,command):
        cmd = command.replace(':text:',self.textEdit.toPlainText())
        cmd = commontags(cmd)
        os.system(cmd)
        self.textEdit.clear()
        
    def urlaction(self,command):
        cmd = command.replace(':url:',self.textEdit.toPlainText())
        cmd = commontags(cmd)
        os.system(cmd)
        self.textEdit.clear()
    
    def fileaction(self,command):
        if 'file://' not in self.textEdit.toPlainText():
            QMessageBox.information(self, "Info", "No file URI found.")
            return
        files = self.textEdit.toPlainText().split('\n')
        for fn in files:
            if fn.startswith('file://'):
                fn = unquote(fn.replace('file://',''))
            if os.path.exists(fn):
                fname = os.path.splitext(os.path.basename(fn))[0]
                fext = os.path.splitext(fn)[1]
                fdir = os.path.dirname(fn)
                
                cmd = command.replace(':file:',fn)
                cmd = commontags(cmd)
                cmd = cmd.replace(":fname:",fname)
                cmd = cmd.replace(":fext:",fext)
                cmd = cmd.replace(":fdir:",fdir)
                
                os.system(cmd)
            else:
                QMessageBox.information(self, "Error", f"File: {fn} doesn't exist.")
              
            
        self.textEdit.clear()
        
    def showDetails(self, items):
        # Show a message box with details of the dropped items
        details = "\n".join(items)
        QMessageBox.information(self, "Dropped Items", f"Details:\n{details}")

    def clearWindow(self):
        # Clear the text edit widget
        self.textEdit.clear()

    def openSettings(self):
        # Show a placeholder for settings
        QMessageBox.information(self, "Settings", "Settings menu is not implemented yet.")

    def showAbout(self):
        # Show about information
        QMessageBox.information(self, "About", "Drag and Drop Example\nVersion 1.0")
        
def savelist2json(lista,filename):
  try:
    with open(filename, 'w+') as outfile:
      json.dump(lista, outfile,indent=2)
    return 0
  except:
    return -1

def loadjson2list(filename):
  try:
    if os.path.exists(filename):
      with open(filename) as json_file:
        jlist = json.load(json_file)
        return jlist
    else:
      return None
  except:
    return None
    
def commontags(s):
    tmp = s
    now = datetime.now()
    tmp = tmp.replace(":timestamp:",now.strftime("%Y%m%d-%H%M%S"))
    tmp = tmp.replace(":year:",now.strftime("%Y"))
    tmp = tmp.replace(":month:",now.strftime("%m"))
    tmp = tmp.replace(":day:",now.strftime("%d"))
    tmp = tmp.replace(":time:",now.strftime("%H%M%S"))
    
    tmp = tmp.replace(":home:",os.environ.get('HOME'))
    tmp = tmp.replace(":user:",os.environ.get('USER'))
    
    if os.environ.get('BROWSER'):
        tmp = tmp.replace(":browser:",os.environ.get('BROWSER'))
    if os.environ.get('EDITOR'):
        tmp = tmp.replace(":editor:",os.environ.get('EDITOR'))
    if os.environ.get('PLAYER'):
        tmp = tmp.replace(":player:",os.environ.get('PLAYER'))        
    return tmp
        
def loadsettings(df):
    global SETTINGS
    if os.path.exists(df):
        SETTINGS = loadjson2list(df)
    elif os.path.exists('settings.json'):
        SETTINGS = loadjson2list('settings.json')
    elif os.path.exists(DIR+'settings.json'):
        SETTINGS = loadjson2list(DIR+'settings.json')
    else:
        SETTINGS = {'background':'255,255,255,0.7',
        'textcolor':'#DDDDDD',
        'fontsize':'14',
        'radius':'10',
        'padding':'10',
        'scroll_color':'#BBBBBB',
        'scroll_width':'5',
        'x':100,
        'y':100,
        'width':100,
        'height':50
        }
        
def loadactions(fn):
    global ACTIONS
    if os.path.exists(fn):
        ACTIONS = loadjson2list(fn)
    elif os.path.exists(DIR+'actions.json'):
        ACTIONS = loadjson2list(DIR+'actions.json')
    else:
        ACTIONS = [{'name':'Copy to clipboard','command':'echo ":text:" | xclip -sel clip','type':'text'},
        {'name':'Open in Browser','command':':browser: ":url:"','type':'url'},
        {'name':'','command':'','type':'separator'},
        {'name':'Open File','command':'xdg-open ":file:"','type':'file'},
        {'name':'Video to MP3','command':'yt-dlp -R5 -c --extract-audio --audio-format=mp3 -P "/home/:user:/Music" ":url:"','type':'url'},
        {'name':'Backup File','command':'zip /home/:user:/:fname:.zip ":file:" -j','type':'file'},
        {'name':'eMail File (Evolution)','command':'evolution mailto:\?attach=":file:"','type':'file'},
        {'name':'eMail File (Thunderbird)','command':'thunderbird -compose attachment=":file:"','type':'file'},
        ]
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Drag'n'Drop utility...",prog='dragster', usage='%(prog)s [-s settings] [-a actions]')
    parser.add_argument('-s','--settings', help='Specify settings.json file',const="", nargs='?')
    parser.add_argument('-a','--actions', help='Specify actions.json file',const="", nargs='?')
    args = parser.parse_args()
    if args.settings == None:
        loadsettings("")
    else:
        loadsettings(args.settings)
    if args.actions == None:
        loadactions("")
    else:
        loadactions(args.actions)
    app = QApplication(sys.argv)
    app.setStyleSheet("QMainWindow { background: transparent; }")  # Transparent background for the main window
    window = DragDropWindow()
    window.show()
    #savelist2json(ACTIONS,"acts.json")
    sys.exit(app.exec_())
    
