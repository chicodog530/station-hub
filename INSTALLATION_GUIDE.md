# Step-by-Step Installation Guide (For Beginners)

Welcome! If you are not a programmer and have never used GitHub or Python before, don't worry. This guide will walk you through exactly how to install and run the Station Hub on your Windows computer in just a few clicks!

---

## Part 1: Downloading the Station Hub

1. On the GitHub page (where you are reading this), look for the bright green button near the top right that says **"<> Code"**.
2. Click that green button.
3. In the dropdown menu that appears, click **"Download ZIP"**.
4. This will download a `.zip` file to your computer (usually into your **Downloads** folder).

## Part 2: Extracting the Files

Your computer downloaded a compressed "ZIP" folder. You need to extract the files before you can use them:
1. Open your **Downloads** folder and find the `station-hub-main.zip` file.
2. **Right-click** on the `.zip` file and select **"Extract All..."**.
3. A window will pop up. Just click the **"Extract"** button at the bottom.
4. Windows will automatically open a new folder containing the extracted files. Open the `station-hub-main` folder inside it so you can see all the files (like `install.bat`, `run.bat`, etc.).

## Part 3: Running the Automated Installer

You need Python installed on your computer for the Hub to work. Don't worry, we wrote a script that does all the hard work for you!

1. In the folder you just extracted, find the file named **`install.bat`** (it might just say `install` and have an icon with gears on it).
2. **Double-click** `install.bat`.
3. A black command prompt window will open.
4. *If Windows gives you a blue warning screen saying "Windows protected your PC", click **"More info"**, and then click **"Run anyway"**.*
5. The script will check if you have Python. If you don't, it will automatically download it from the internet and install it silently in the background. It will also automatically download all the required audio libraries.
6. Once it says "Installation Complete!", you can close the black window. You only ever have to do this step once!

## Part 4: Starting the Hub

Whenever you want to use your radio over the network:
1. Make sure your radio (e.g., Yaesu FT-710) is connected to your computer via USB.
2. Open the `station-hub-main` folder.
3. **Double-click** the **`run.bat`** file.
4. A black window will open, and the Hub will automatically connect to your radio. Leave this window open in the background while you are operating!

---

## Part 5: Installing the Android Walkie-Talkie App

We have included a pre-built Android app so you can talk on your radio from your phone!

1. Take your Android phone's charging cable and plug your phone into your computer's USB port.
2. On your phone screen, it might ask you what to do with the USB connection. Select **"File Transfer"** or **"MTP"**.
3. On your computer, inside the `station-hub-main` folder, find the file named **`ssb-walkie.apk`**.
4. **Right-click** `ssb-walkie.apk` and select **Copy**.
5. Open **"This PC"** (or "My Computer") on Windows, find your phone in the list of drives, and open it.
6. Open your phone's **"Download"** folder and **Paste** the file there.
7. Unplug your phone from the computer.
8. On your phone, open your **"Files"** or **"My Files"** app, go to the Downloads folder, and tap on **`ssb-walkie.apk`**.
9. *Note: Android prevents installing apps from outside the Google Play Store by default. A warning will pop up. Tap **"Settings"**, flip the switch for **"Allow from this source"**, tap the back arrow, and hit **"Install"**.*
