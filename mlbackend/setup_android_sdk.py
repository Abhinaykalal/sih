import os
import shutil
import urllib.request
import zipfile

def setup_sdk():
    sdk_root = "F:/Android/Sdk"
    cmdline_dir = os.path.join(sdk_root, "cmdline-tools")
    latest_dir = os.path.join(cmdline_dir, "latest")
    zip_path = "F:/cmdline-tools.zip"

    os.makedirs(cmdline_dir, exist_ok=True)
    print("1. Downloading official Google Android Command-Line Tools (~150MB)...")
    url = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
    urllib.request.urlretrieve(url, zip_path)
    print("Download complete!")

    print("2. Extracting to", cmdline_dir)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(cmdline_dir)

    extracted_subfolder = os.path.join(cmdline_dir, "cmdline-tools")
    if os.path.exists(latest_dir):
        shutil.rmtree(latest_dir)
    os.rename(extracted_subfolder, latest_dir)

    if os.path.exists(zip_path):
        os.remove(zip_path)

    print("3. Command-Line Tools extracted to:", latest_dir)

if __name__ == "__main__":
    setup_sdk()
