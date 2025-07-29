import os
import subprocess
import requests
import time
import sys
import logging
import shutil # For creating and deleting directories if needed

# --- SCRIPT VERSION ---
SCRIPT_VERSION = "1.3.1" # Current script version

# --- DEBUG MESSAGES AT SCRIPT START ---
# These print() calls are made before logging setup to ensure Python starts the file.
print("Script started: Initializing...")
sys.stdout.flush() # Force flush output buffer

# --- LOGGING SETUP ---
log_dir = "logs"
# Remove log directory at each start
if os.path.exists(log_dir):
    try:
        shutil.rmtree(log_dir)
        print(f"DEBUG: Removed existing log directory: {log_dir}")
        sys.stdout.flush()
    except OSError as e:
        print(f"ERROR: Could not remove log directory '{log_dir}': {e}")
        print("Continuing without clearing old logs. Check permissions for the 'logs' directory.")
        sys.stdout.flush()

try:
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print(f"DEBUG: Created log directory: {log_dir}")
        sys.stdout.flush()
except OSError as e:
    print(f"ERROR: Could not create log directory '{log_dir}': {e}")
    print("Continuing without file logging. Check permissions for the 'logs' directory.")
    sys.stdout.flush()
    # If log folder creation fails, configure logging only to console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.error(f"Failed to create log directory '{log_dir}'. Log file will not be created.")
    # Skip the rest of the file logging setup
    pass
else:
    log_filename = os.path.join(log_dir, "installer.log")
    # Try to open the log file for writing to check permissions
    try:
        with open(log_filename, 'a', encoding='utf-8') as f:
            f.write("\n--- Script execution started ---\n") # Add a separator for new run
        print(f"DEBUG: Log file '{log_filename}' opened successfully for writing.")
        sys.stdout.flush()
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
    except IOError as e:
        print(f"ERROR: Could not write to log file '{log_filename}': {e}")
        print("Continuing without file logging. Check permissions for the 'logs' directory.")
        sys.stdout.flush()
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        logging.error(f"Failed to write to log file '{log_filename}'. Log file will not be updated.")

logging.info("Logging configured.")
print("DEBUG: Logging configured message printed.") # Additional debug message
sys.stdout.flush()

# --- PROJECT CONFIGURATION ---
# Base URL for your APKs on GitHub Releases.
# Ensure this is the exact link to your release tag containing the APKs.
BASE_APK_RELEASE_URL = "https://github.com/AleXDE54/liteageOS/releases/download/APKS/"

# Applications from your list: {APK filename: (Description, Optional)}
# *NOTE*: Package names will be AUTOMATICALLY determined from APK files using 'aapt'.
# Ensure 'aapt' is installed and accessible (see instructions below).
# 'Optional' (True/False) indicates whether the script will ask the user to install this app.
LINEAGEOS_COMPONENTS = {
    "Music.apk": ("Music Player", False),
    "Phone.apk": ("Phone App", False),
    "Files.apk": ("File Manager", False),
    "Browser.apk": ("Web Browser", False),
    "Calc.apk": ("Calculator", False),
    "Recorder.apk": ("Audio Recorder", False),
    "Calender.apk": ("Calendar", False),
    "Gallery.apk": ("Gallery Viewer", False),
    "Aurora.apk": ("Aurora Store (App Store)", True),
}

# Launchers for selection
LAUNCHERS = {
    "Litechair.apk": "Litechair (Modern Lawnchair Fork)",
    "Litechair_legacy.apk": "Litechair Legacy (Android 5.0 Design)"
}

# Wallpaper filename on GitHub
WALLPAPER_FILENAME = "wallpaper.jpg"

# --- GLOBAL VARIABLES ---
# Path to the ADB executable.
# The script will look for 'adb' in the system PATH variable.
# If 'adb' is not found, ensure Android SDK Platform-Tools is added to PATH.
ADB_PATH = "adb"

# Path to the AAPT (Android Asset Packaging Tool) executable.
# The script will look for 'aapt' in the system PATH variable.
# If 'aapt' is not found, ensure Android SDK Build-Tools is added to PATH.
AAPT_PATH = "aapt"

# Changed to 'apks'
TEMP_DIR = "apks" # Temporary folder for downloading APKs (will not be deleted)

# Flag to track AAPT availability
aapt_available = False

# --- FUNCTIONS ---

def clear_console():
    """Clears the console."""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_step(message):
    """Prints a step message and logs it."""
    logging.info(f"\n--- {message} ---")

def run_command(command, check_output=False, suppress_error=False, tool_name="ADB"):
    """
    Executes a command (ADB or AAPT) and returns the result.
    :param command: List of strings representing the command and its arguments.
    :param check_output: If True, returns the command's stdout.
    :param suppress_error: If True, does not print stderr on errors.
    :param tool_name: Name of the tool (for error messages).
    :return: Command output (if check_output=True) or True/False for success/failure.
    """
    full_command = command
    logging.info(f"Executing {tool_name} command: {' '.join(full_command)}")
    try:
        if check_output:
            result = subprocess.run(full_command, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore')
            # Always print stdout as it may contain useful information
            if result.stdout:
                logging.info(f"{tool_name} Output (stdout): {result.stdout.strip()}")
            # Safely handle stderr if it's None
            if result.stderr:
                logging.warning(f"{tool_name} Error (stderr): {result.stderr.strip()}")
            elif not suppress_error and not result.stdout: # If both are empty but not suppressing errors
                logging.warning(f"{tool_name} Error (stdout/stderr): (empty)")
            return result.stdout.strip()
        else:
            subprocess.run(full_command, check=True, encoding='utf-8', errors='ignore')
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Error executing {tool_name} command: {e}")
        # Safely handle stdout and stderr
        if e.stdout:
            logging.error(f"Stdout: {e.stdout.strip()}")
        if e.stderr:
            logging.error(f"Stderr: {e.stderr.strip()}")
        if not e.stdout and not e.stderr:
            logging.error("Error output (stdout/stderr) is empty or unavailable.")
        return False
    except FileNotFoundError:
        logging.critical(f"Error: Command '{command[0]}' ({tool_name}) not found.")
        if tool_name == "AAPT":
            logging.critical("Automatic package name detection is not possible without AAPT.")
            logging.critical("Please install Android SDK Build-Tools and ensure 'aapt' is available in your system PATH.")
        else: # For ADB
            logging.critical("Ensure ADB is installed and added to your system PATH.")
        sys.exit(1) # Exit if ADB is not found, as the script cannot function without it

def check_adb_connection():
    """Checks ADB connection and device authorization."""
    print_step("Checking ADB Connection")
    output = run_command([ADB_PATH, "devices"], check_output=True, tool_name="ADB")
    if not output or "device" not in output or "unauthorized" in output:
        logging.error("\nERROR: Device not connected or unauthorized.")
        logging.error("Ensure that:")
        logging.error("1. 'USB Debugging' is enabled on your phone in 'Developer Options'.")
        logging.error("2. Your phone is connected to the PC via USB.")
        logging.error("3. You have allowed 'Allow USB debugging' on your phone screen when prompted.")
        logging.error("4. ADB is installed and available in your system PATH (try 'adb devices' in command prompt).")
        input("Press Enter after resolving the issue and try again...")
        return check_adb_connection() # Recursive call to re-check
    logging.info("ADB device connected and authorized.")
    return True

def check_aapt_availability():
    """Checks if AAPT is available."""
    global aapt_available
    print_step("Checking AAPT Availability")
    # Try to execute a simple aapt command to check its presence
    if run_command([AAPT_PATH, "version"], check_output=True, suppress_error=True, tool_name="AAPT"):
        aapt_available = True
        logging.info("AAPT found. Automatic package name detection will work.")
    else:
        aapt_available = False
        logging.warning("AAPT not found. Automatic package name detection will be unavailable.")
        logging.warning("You might need to manually set the default launcher and verify package names for uninstallation.")
        logging.warning("To install AAPT: download Android SDK Command-line Tools from developer.android.com/studio/releases/platform-tools")
        logging.warning("Unzip and add the path to the 'build-tools' folder to your system PATH.")
    return aapt_available

def get_package_name_from_apk(apk_path):
    """
    Extracts the package name from an APK file using aapt.
    :param apk_path: Path to the APK file.
    :return: Package name or None if extraction failed.
    """
    if not aapt_available:
        logging.warning("AAPT is unavailable. Cannot automatically determine package name.")
        return None

    logging.info(f"Determining package name for {os.path.basename(apk_path)} using aapt...")
    try:
        output = run_command([AAPT_PATH, "dump", "badging", apk_path], check_output=True, suppress_error=True, tool_name="AAPT")
        if output:
            for line in output.splitlines():
                if "package: name=" in line:
                    package_name = line.split("name='")[1].split("'")[0]
                    logging.info(f"Package name for {os.path.basename(apk_path)}: {package_name}")
                    return package_name
        logging.warning(f"Failed to determine package name for {os.path.basename(apk_path)}. Please check the APK file.")
        return None
    except Exception as e:
        logging.error(f"Error extracting package name from {apk_path}: {e}")
        return None

def download_file(url, filename, target_dir):
    """
    Downloads a file from the specified URL.
    :param url: URL to download the file from.
    :param filename: Name of the file to save.
    :param target_dir: Target folder to save the file.
    :return: Path to the downloaded file or None on error.
    """
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        logging.info(f"Created directory: {target_dir}")

    filepath = os.path.join(target_dir, filename)

    # Check if the file already exists
    if os.path.exists(filepath):
        logging.info(f"File '{filename}' already exists in '{target_dir}'. Skipping download.")
        return filepath

    logging.info(f"Downloading {filename} from {url} to {target_dir}...")
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status() # Raises an exception for bad HTTP statuses

        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        logging.info(f"Successfully downloaded {filename}.")
        return filepath
    except requests.exceptions.RequestException as e:
        logging.error(f"Error downloading {filename}: {e}")
        return None

def push_and_install_apk(local_path, remote_path="/data/local/tmp/"):
    """
    Pushes an APK to the device and installs it.
    :param local_path: Local path to the APK file.
    :param remote_path: Remote path on the device for temporary APK storage.
    :return: True on success, False on error.
    """
    filename = os.path.basename(local_path)
    remote_apk_path = os.path.join(remote_path, filename)

    logging.info(f"Pushing {filename} to device...")
    if not run_command([ADB_PATH, "push", local_path, remote_apk_path], tool_name="ADB"):
        logging.error(f"Failed to push {filename} to device.")
        return False

    logging.info(f"Installing {filename}...")
    # Use 'pm install -r' to update if already installed.
    # If the app is already installed with a different signature, this will cause an error.
    if not run_command([ADB_PATH, "shell", "pm", "install", "-r", remote_apk_path], tool_name="ADB"):
        logging.error(f"Error installing {filename}. It might require manual installation, or the app is already installed with a different signature, or it's a split-APK.")
        logging.error("Try to find a 'universal' APK for this app or install it manually.")
        return False
    logging.info(f"Successfully installed {filename}.")
    return True

def set_default_launcher(package_name):
    """
    Sets the specified launcher as the default.
    :param package_name: The package name of the launcher.
    :return: True on success, False on error.
    """
    if not package_name:
        logging.error("Cannot set default launcher: package name not determined.")
        logging.info("Please set the default launcher manually: Settings -> Apps -> Default apps -> Home app -> {Your Launcher Name}.")
        return False

    logging.info(f"Attempting to set {package_name} as default launcher...")
    # This command might require the exact component activity name (e.g., com.package.name/.MainActivity),
    # but for most launchers, the package name is sufficient.
    if run_command([ADB_PATH, "shell", "cmd", "package", "set-home-activity", package_name], tool_name="ADB"):
        logging.info(f"Successfully set {package_name} as default launcher.")
        return True
    else:
        logging.error(f"Failed to set {package_name} as default launcher automatically.")
        logging.info("You might need to do this manually: Settings -> Apps -> Default apps -> Home app -> {Your Launcher Name}.")
        return False

def set_wallpaper(local_image_path):
    """
    Sets an image as the device wallpaper.
    :param local_image_path: Local path to the image file.
    :return: True on success, False on error.
    """
    remote_wallpaper_path = "/sdcard/Download/" + os.path.basename(local_image_path)
    logging.info(f"Pushing wallpaper {os.path.basename(local_image_path)} to device at {remote_wallpaper_path}...")
    if not run_command([ADB_PATH, "push", local_image_path, remote_wallpaper_path], tool_name="ADB"):
        logging.error(f"Failed to push wallpaper {os.path.basename(local_image_path)} to device.")
        return False

    logging.info(f"Attempting to set wallpaper from {remote_wallpaper_path}...")
    # Use 'cmd wallpaper set' for Android 7.0+
    if run_command([ADB_PATH, "shell", "cmd", "wallpaper", "set", remote_wallpaper_path], tool_name="ADB"):
        logging.info("Wallpaper successfully set.")
        return True
    else:
        logging.error("Failed to set wallpaper automatically.")
        logging.info(f"Please set the wallpaper manually: open 'Gallery' or 'Files' app on your phone, find '{os.path.basename(local_image_path)}' in 'Download' folder and set it as wallpaper.")
        return False

def setup_temp_dir():
    """Creates the temporary APK directory."""
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)
        logging.info(f"Created directory: {TEMP_DIR}")
    else:
        logging.info(f"Temporary directory '{TEMP_DIR}' already exists.")

def get_android_os_version():
    """Gets the Android OS version from the device."""
    logging.info("Getting Android OS version...")
    # Try to get the Android release version (e.g., "13")
    release_version_str = run_command([ADB_PATH, "shell", "getprop", "ro.build.version.release"], check_output=True, suppress_error=True, tool_name="ADB")
    if release_version_str:
        try:
            # Some devices might return non-numeric values (e.g., "13")
            # Try to convert to int if possible
            return int(release_version_str.strip())
        except ValueError:
            logging.warning(f"Could not convert Android release version '{release_version_str.strip()}' to number. Attempting to get API level.")
            pass # Continue to get API level

    # If release version failed or was non-numeric, try API level
    sdk_version_str = run_command([ADB_PATH, "shell", "getprop", "ro.build.version.sdk"], check_output=True, suppress_error=True, tool_name="ADB")
    if sdk_version_str and sdk_version_str.strip().isdigit():
        logging.info(f"Android Version (API Level): {sdk_version_str.strip()}")
        # Approximate mapping from API level to Android version number
        api_level = int(sdk_version_str.strip())
        if api_level >= 34: return 14 # Android 14
        if api_level == 33: return 13 # Android 13
        if api_level == 32: return 12 # Android 12L
        if api_level == 31: return 12 # Android 12
        if api_level == 30: return 11 # Android 11
        if api_level == 29: return 10 # Android 10
        if api_level == 28: return 9  # Android 9
        if api_level == 27: return 8  # Android 8.1
        if api_level == 26: return 8  # Android 8.0
        logging.warning(f"Unknown API Level: {api_level}. Returning API level as version.")
        return api_level
    else:
        logging.error("Failed to get Android OS version from getprop.")
        return None
    
def check_arm8_support_on_device():
    """Checks for ARM8 support on the device."""
    logging.info("Checking for ARM8 support...")
    # Check ro.product.cpu.abi and ro.product.cpu.abi2
    abi_output = run_command([ADB_PATH, "shell", "getprop", "ro.product.cpu.abi"], check_output=True, suppress_error=True, tool_name="ADB")
    abi2_output = run_command([ADB_PATH, "shell", "getprop", "ro.product.cpu.abi2"], check_output=True, suppress_error=True, tool_name="ADB")

    if (abi_output and "arm64-v8a" in abi_output.lower()) or \
       (abi2_output and "arm64-v8a" in abi2_output.lower()):
        logging.info("ARM8 support (arm64-v8a) detected.")
        return True
    logging.info("ARM8 support (arm64-v8a) not detected.")
    return False

def get_device_ram_gb():
    """Gets the total device RAM in GB."""
    logging.info("Getting total device RAM...")
    meminfo_output = run_command([ADB_PATH, "shell", "cat", "/proc/meminfo"], check_output=True, suppress_error=True, tool_name="ADB")
    if meminfo_output:
        for line in meminfo_output.splitlines():
            if "MemTotal:" in line:
                try:
                    # MemTotal:         3858000 kB (example)
                    mem_kb = int(line.split()[1])
                    mem_gb = round(mem_kb / (1024 * 1024), 2)
                    logging.info(f"Total RAM: {mem_gb} GB.")
                    return mem_gb
                except (ValueError, IndexError):
                    logging.error(f"Failed to parse MemTotal from line: {line}")
                    return None
    logging.error("Failed to get RAM information.")
    return None

def calculate_liteageos_version(android_version_num, has_arm8, is_memory_less_than_100gb):
    """
    Calculates the LiteageOS version based on rules.
    Rules:
    1. Base version = Android Version + 10
    2. If ARM8 is supported, append "+"
    3. If memory is less than 100 GB, append "S"
    """
    version = ""
    if android_version_num is not None:
        version += str(android_version_num + 10)
    else:
        version += "???" # If Android version could not be retrieved

    if has_arm8:
        version += "+"

    if is_memory_less_than_100gb:
        version += "S"
    
    return version

def install_liteageos_components(install_launcher_action, chosen_launcher_apk, install_optional_apps_config):
    """
    Function to install all LiteageOS components.
    Accepts pre-configured settings.
    """
    # --- Install selected launcher ---
    print_step("Installing Launcher")
    if install_launcher_action:
        logging.info(f"Selected launcher: {chosen_launcher_apk}")

        launcher_url = BASE_APK_RELEASE_URL + chosen_launcher_apk
        launcher_local_path = os.path.join(TEMP_DIR, chosen_launcher_apk) # Path for the actual APK

        # Step 1: Ensure the APK is downloaded locally.
        downloaded_path = download_file(launcher_url, chosen_launcher_apk, TEMP_DIR)
        
        if not downloaded_path:
            logging.error(f"Failed to download launcher '{chosen_launcher_apk}'. Check URL or internet connection.")
            logging.info("Skipping launcher installation.")
        else:
            # Step 2: Get package name from the downloaded APK.
            launcher_package_name = get_package_name_from_apk(downloaded_path)

            if launcher_package_name:
                # Step 3: Check if the launcher is already installed on the device.
                is_installed_on_device = run_command([ADB_PATH, "shell", "pm", "path", launcher_package_name], check_output=True, suppress_error=True, tool_name="ADB")
                
                if is_installed_on_device and "package:" in is_installed_on_device:
                    logging.info(f"\nDetected already installed launcher with package name '{launcher_package_name}'.")
                    make_default = input("It is already installed. Do you want to set it as the default launcher (y/n)? ").lower()
                    if make_default == 'y':
                        set_default_launcher(launcher_package_name)
                    else:
                        logging.info("Skipping setting default launcher as it's already installed and you chose not to make it primary.")
                else:
                    logging.info(f"Launcher '{launcher_package_name}' not found on device. Proceeding with installation.")
                    # Step 4: Push and install the APK.
                    if push_and_install_apk(downloaded_path):
                        logging.info("Launcher installed. Now attempting to set it as the default launcher.")
                        set_default_launcher(launcher_package_name)
                    else:
                        logging.error("Failed to install launcher. Check messages above. It might be a split-APK requiring full build, or a signature conflict.")
                        logging.info("Try to find a 'universal' APK for this launcher or install it manually.")
            else:
                logging.error(f"ERROR: Failed to determine package name for {chosen_launcher_apk}. Setting default launcher might not work.")
                logging.info("Please ensure your selected launcher APK is a valid APK file and that AAPT is working correctly.")
    else:
        logging.info("Skipping launcher installation as per user choice.")


    # --- Install other LineageOS Applications ---
    print_step("Installing LineageOS Applications")
    for apk_filename, (description, optional) in LINEAGEOS_COMPONENTS.items(): # Corrected typo here
        # Skip launchers as they are handled separately
        if apk_filename in LAUNCHERS: 
            continue

        install_app = 'n' # Default to not install
        if not optional: # Mandatory apps are always installed
            install_app = 'y'
        elif optional and install_optional_apps_config == 'y': # Optional apps, if user chose 'y'
            install_app = 'y'
        
        if install_app == 'y':
            logging.info(f"\nInstalling {description} ({apk_filename})...")
            app_url = BASE_APK_RELEASE_URL + apk_filename
            local_path = download_file(app_url, apk_filename, TEMP_DIR) # download_file will check for existence
            if local_path:
                package_name_for_app = get_package_name_from_apk(local_path) # Automatically determine package name
                if push_and_install_apk(local_path):
                    logging.info(f"{description} successfully installed.")
            else:
                logging.error(f"Failed to download {description}. Check URL.")
        else:
            logging.info(f"Skipping installation of {description}.")


    # --- Install Wallpaper ---
    print_step("Installing Wallpaper")
    wallpaper_url = BASE_APK_RELEASE_URL + WALLPAPER_FILENAME
    local_wallpaper_path = download_file(wallpaper_url, WALLPAPER_FILENAME, TEMP_DIR) # download_file will check for existence
    if local_wallpaper_path:
        set_wallpaper(local_wallpaper_path)
    else:
        logging.error("Failed to download wallpaper file. Wallpaper will not be set.")

    logging.info("\n--- LiteageOS Installation Complete! ---")
    logging.info("Please check your phone. Additional manual launcher setup might be required.")

def wipe_liteageos_components():
    """Function to uninstall all LiteageOS components (launchers and apps)."""
    print_step("Starting LiteageOS Uninstallation Function")
    confirm = input("Are you sure you want to uninstall all LiteageOS components (launchers, apps)? This action is irreversible (y/n)? ").lower()
    if confirm != 'y':
        logging.info("Uninstallation cancelled by user.")
        return

    packages_to_uninstall = []

    # Add known launcher package names for uninstallation
    packages_to_uninstall.append("app.lawnchair.nightly")
    packages_to_uninstall.append("ch.deletescape.lawnchair") # Correct package name for Litechair Legacy

    # Collect package names of other apps from LINEAGEOS_COMPONENTS
    for apk_filename in LINEAGEOS_COMPONENTS.keys():
        local_path = os.path.join(TEMP_DIR, apk_filename)
        # Attempt to download if not present, to get package name
        if not os.path.exists(local_path):
            download_file(BASE_APK_RELEASE_URL + apk_filename, apk_filename, TEMP_DIR)
        
        if os.path.exists(local_path):
            package_name = get_package_name_from_apk(local_path)
            if package_name:
                packages_to_uninstall.append(package_name)
            else:
                logging.warning(f"Failed to determine package name for {apk_filename}. Skipping uninstallation.")
        else:
            logging.warning(f"File {apk_filename} not found locally to determine package name. Skipping uninstallation.")

    # Add specific packages requested by the user for forced uninstallation
    packages_to_uninstall.append("org.lineageos.etar") # Calendar
    packages_to_uninstall.append("org.lineageos.aperture.dev") # Camera
    packages_to_uninstall.append("com.android.deskclock") # Clock

    print_step("Uninstalling LiteageOS components...")
    for package in set(packages_to_uninstall): # Use set to remove duplicates
        logging.info(f"Attempting to uninstall package: {package}")
        # Use --user 0 to uninstall for the current user
        if run_command([ADB_PATH, "shell", "pm", "uninstall", "--user", "0", package], suppress_error=True, tool_name="ADB"):
            logging.info(f"Package {package} successfully uninstalled (for current user).")
        else:
            logging.warning(f"Failed to uninstall package {package}. It might not be installed or is a system app.")

    logging.info("LiteageOS uninstallation process complete.")


def main():
    print("DEBUG: Entering main function.") # Debug message
    sys.stdout.flush()
    logging.info("DEBUG: Entering main function (logged).") # Debug message to log

    print(f"--- LiteageOS Installer (Script Version: {SCRIPT_VERSION}) ---") # Display script version
    sys.stdout.flush()

    try: # General try-except block for the entire main function
        setup_temp_dir()

        if not check_adb_connection():
            sys.exit(1)

        check_aapt_availability()

        # --- Main action menu (displayed first) ---
        while True:
            # Clear console before each main menu display
            clear_console()
            print(f"--- LiteageOS Installer (Script Version: {SCRIPT_VERSION}) ---") # Repeat header after clearing

            # Predict LiteageOS version (displayed at the top of the menu)
            print_step("Predicting LiteageOS Version for your Device")
            android_os_version = get_android_os_version()
            has_arm8_support = check_arm8_support_on_device()
            total_ram_gb = get_device_ram_gb()
            is_memory_less_than_100gb = False
            if total_ram_gb is not None:
                is_memory_less_than_100gb = total_ram_gb < 100

            predicted_liteage_version = calculate_liteageos_version(
                android_os_version,
                has_arm8_support,
                is_memory_less_than_100gb
            )
            print(f"The LiteageOS version that can be installed on your device is: {predicted_liteage_version}")
            logging.info(f"Predicted LiteageOS version for installation: {predicted_liteage_version}")
            
            print_step("Choose an action:")
            print("1. Install/Update LiteageOS Components")
            print("2. Uninstall LiteageOS Components")
            print("3. Exit")
            
            choice = input("Enter action number: ").strip()

            if choice == '1':
                # --- Pre-configuration: "yes/no" questions ---
                print_step("Installation Pre-configuration")
                
                # Launcher configuration
                install_launcher_config = False
                chosen_launcher_apk_config = None
                launcher_action_input = input("Do you want to install or change the launcher (y/n)? ").lower()
                if launcher_action_input == 'y':
                    install_launcher_config = True
                    launcher_choice = ""
                    while launcher_choice not in ['1', '2']:
                        print("Select launcher to install:")
                        print(f"1. {LAUNCHERS['Litechair.apk']}")
                        print(f"2. {LAUNCHERS['Litechair_legacy.apk']}")
                        launcher_choice = input("Enter number (1 or 2): ").strip()
                    chosen_launcher_apk_config = "Litechair.apk" if launcher_choice == '1' else "Litechair_legacy.apk"
                
                # Optional apps configuration
                # 'y' - install all optional, 'n' - skip all optional
                install_optional_apps_config = input("Do you want to install Aurora Store? (y/n) ").lower()
                while install_optional_apps_config not in ['y', 'n']:
                    install_optional_apps_config = input("Invalid input. Please enter 'y' or 'n': ").lower()

                # Call installation function with collected settings
                install_liteageos_components(install_launcher_config, chosen_launcher_apk_config, install_optional_apps_config)
            elif choice == '2':
                wipe_liteageos_components()
            elif choice == '3':
                logging.info("Exiting script.")
                break
            else:
                print("Invalid choice. Please enter 1, 2 or 3.")
            
            input("\nPress Enter to continue to the main menu...") # Pause before returning to menu


    except Exception as e:
        # If any unhandled error occurred in main()
        logging.critical(f"Critical error in main() function: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: The script terminated due to an unexpected error. Check the log file '{log_filename}' for details.")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
