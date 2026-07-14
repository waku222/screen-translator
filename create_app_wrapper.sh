#!/bin/bash

# Configuration
APP_NAME="ScreenTranslator"
SCRIPT_TO_RUN="$(pwd)/start.sh"
ICON_SOURCE="/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/ScreenSharingIcon.icns" # Optional: generic icon

# 1. Create the AppleScript application wrapper
echo "Creating $APP_NAME.app..."
osacompile -o "$APP_NAME.app" -e "do shell script \"'$SCRIPT_TO_RUN' > /dev/null 2>&1 &\""

# 2. (Optional) Set a better icon if available
if [ -f "$ICON_SOURCE" ]; then
    echo "Setting icon..."
    cp "$ICON_SOURCE" "$APP_NAME.app/Contents/Resources/applet.icns"
fi

# 3. Update Info.plist to hide from Dock (optional, but good for background apps)
# defaults write "$(pwd)/$APP_NAME.app/Contents/Info.plist" LSUIElement -bool true

echo "Done! You can now move $APP_NAME.app to your Applications folder or keep it here."
echo "IMPORTANT: The first time you run it, you will need to grant Screen Recording permissions."
