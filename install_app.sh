#!/bin/bash

# Configuration
APP_NAME="ScreenTranslator.app"
SOURCE_APP="$(pwd)/$APP_NAME"
DEST_DIR="/Applications"
OLD_PLIST="$HOME/Library/LaunchAgents/com.user.start.translation.plist"

echo "=== Installing Screen Translator ==="

# 1. Clean up old LaunchAgent if exists
if [ -f "$OLD_PLIST" ]; then
    echo "Removing old Launch Agent..."
    launchctl unload "$OLD_PLIST" 2>/dev/null || true
    rm "$OLD_PLIST"
    echo "Old background service removed."
fi

# 2. Ensure App exists
if [ ! -d "$SOURCE_APP" ]; then
    echo "Building App..."
    ./create_app_wrapper.sh
fi

# 3. Install to Applications
echo "Installing $APP_NAME to $DEST_DIR..."
if [ -d "$DEST_DIR/$APP_NAME" ]; then
    echo "Removing existing installation..."
    rm -rf "$DEST_DIR/$APP_NAME"
fi

cp -r "$SOURCE_APP" "$DEST_DIR/"

echo "=== Installation Complete! ==="
echo "1. The app is now in your Applications folder."
echo "2. Please double-click '$DEST_DIR/$APP_NAME' to start it."
echo "3. Grant 'Screen Recording' permission when prompted."
echo "4. To start automatically at login, go to System Settings > General > Login Items and add ScreenTranslator."
