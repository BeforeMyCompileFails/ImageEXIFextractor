#!/usr/bin/env python3
"""
EXIF Data Extractor - Extracts all available EXIF data from images in a folder.
Saves the EXIF information to .txt files named after the original image files.
by Denis (BeforeMyCompileFails) 2025
"""

import os
import sys
import io
import subprocess
from PIL import Image, ExifTags
import piexif
import argparse
from datetime import datetime
import json
import re

# Try to import additional libraries for more comprehensive extraction
try:
    import exifread
except ImportError:
    exifread = None

# Disable PyExifTool as it's causing hangs
exiftool = None


def extract_all_exif(image_path, exiftool_path=None):
    """
    Extract all available EXIF data from an image file using multiple methods
    to ensure maximum information extraction.
    """
    exif_data = {}
    filename = os.path.basename(image_path)
    
    # Add file metadata
    file_stat = os.stat(image_path)
    exif_data["FILE_SIZE"] = file_stat.st_size
    exif_data["FILE_CREATED"] = datetime.fromtimestamp(file_stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
    exif_data["FILE_MODIFIED"] = datetime.fromtimestamp(file_stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
    exif_data["FILE_NAME"] = filename
    
    # Method 1: Using PIL's built-in EXIF extraction
    try:
        with Image.open(image_path) as img:
            # Get standard EXIF data if available
            if hasattr(img, '_getexif') and img._getexif():
                exif_info = img._getexif()
                if exif_info:
                    for tag, value in exif_info.items():
                        tag_name = ExifTags.TAGS.get(tag, tag)
                        exif_data[f"PIL_{tag_name}"] = value
            
            # Get all image info including ICC profile data
            exif_data["PIL_FORMAT"] = img.format
            exif_data["PIL_MODE"] = img.mode
            exif_data["PIL_SIZE"] = img.size
            exif_data["PIL_WIDTH"] = img.width
            exif_data["PIL_HEIGHT"] = img.height
            
            # Extract ICC profile information if present
            if "icc_profile" in img.info:
                exif_data["ICC_PROFILE_PRESENT"] = True
                exif_data["ICC_PROFILE_SIZE"] = len(img.info["icc_profile"])
                
                # Try to extract profile date/time from ICC
                try:
                    icc_data = img.info["icc_profile"]
                    # Look for date and time strings in the ICC profile
                    text = icc_data.decode('ascii', errors='ignore')
                    
                    # Extract profile creation datetime (common formats)
                    date_matches = re.findall(r'\d{4}[-/]\d{2}[-/]\d{2}', text)
                    time_matches = re.findall(r'\d{2}:\d{2}:\d{2}', text)
                    
                    if date_matches:
                        exif_data["ICC_PROFILE_DATE"] = date_matches[0]
                    if time_matches:
                        exif_data["ICC_PROFILE_TIME"] = time_matches[0]
                    
                    # Look specifically for profile_date_time patterns
                    profile_dt_match = re.search(r'profile_date_time[:\s]+([^\n]+)', text, re.IGNORECASE)
                    if profile_dt_match:
                        exif_data["PROFILE_DATE_TIME"] = profile_dt_match.group(1).strip()
                except Exception as e:
                    exif_data["ICC_PROFILE_PARSE_ERROR"] = str(e)
            
            # Get ALL image info items, including metadata profiles
            for k, v in img.info.items():
                if isinstance(v, (str, int, float, tuple, list, bool)):
                    exif_data[f"INFO_{k}"] = v
                elif isinstance(v, bytes) and len(v) < 1000:  # Only process reasonably sized byte data
                    try:
                        # Try to decode as string
                        decoded = v.decode('utf-8', errors='ignore')
                        # Look for date/time information
                        if "date" in k.lower() or "time" in k.lower():
                            exif_data[f"INFO_{k}"] = decoded
                    except:
                        exif_data[f"INFO_{k}_SIZE"] = len(v)
    except Exception as e:
        exif_data["PIL_ERROR"] = str(e)
    
    # Method 2: Using piexif for more detailed EXIF extraction
    try:
        exif_dict = piexif.load(image_path)
        
        # Process each EXIF directory
        for ifd_name in ("0th", "Exif", "GPS", "1st", "Interop"):
            if ifd_name in exif_dict and exif_dict[ifd_name]:
                for tag, value in exif_dict[ifd_name].items():
                    # Get tag name if possible
                    if ifd_name == "0th":
                        tag_name = piexif.TAGS["0th"].get(tag, {}).get("name", tag)
                    elif ifd_name == "Exif":
                        tag_name = piexif.TAGS["Exif"].get(tag, {}).get("name", tag)
                    elif ifd_name == "GPS":
                        tag_name = piexif.TAGS["GPS"].get(tag, {}).get("name", tag)
                    elif ifd_name == "1st":
                        tag_name = piexif.TAGS["1st"].get(tag, {}).get("name", tag)
                    elif ifd_name == "Interop":
                        tag_name = piexif.TAGS["Interop"].get(tag, {}).get("name", tag)
                    else:
                        tag_name = str(tag)
                    
                    # Handle different types of values
                    if isinstance(value, bytes):
                        try:
                            # Try to decode as string
                            decoded_value = value.decode('utf-8', errors='replace')
                            exif_data[f"{ifd_name}_{tag_name}"] = decoded_value
                            
                            # Look for profile date time in decoded strings
                            if "profile" in decoded_value.lower() and ("date" in decoded_value.lower() or "time" in decoded_value.lower()):
                                exif_data["DECODED_PROFILE_DATE_TIME"] = decoded_value
                        except:
                            # If can't decode, store as hex representation
                            exif_data[f"{ifd_name}_{tag_name}"] = value.hex()
                    else:
                        exif_data[f"{ifd_name}_{tag_name}"] = value
        
        # Handle thumbnail if present
        if "thumbnail" in exif_dict and exif_dict["thumbnail"]:
            exif_data["THUMBNAIL_PRESENT"] = True
            exif_data["THUMBNAIL_SIZE"] = len(exif_dict["thumbnail"])
    except Exception as e:
        exif_data["PIEXIF_ERROR"] = str(e)
    
    # Method 3: Using exifread if available
    if exifread:
        try:
            with open(image_path, 'rb') as f:
                tags = exifread.process_file(f, details=True)
                for tag, value in tags.items():
                    exif_data[f"EXIFREAD_{tag}"] = str(value)
        except Exception as e:
            exif_data["EXIFREAD_ERROR"] = str(e)
    
    # Method 4: Using exiftool if available (most comprehensive)
    if exiftool:
        try:
            with exiftool.ExifTool() as et:
                # Check if exiftool is properly installed
                if et.run():
                    metadata = et.get_metadata(image_path)
                    for tag, value in metadata.items():
                        # Clean up tag name
                        clean_tag = tag.replace(":", "_").replace(" ", "_")
                        exif_data[f"EXIFTOOL_{clean_tag}"] = value
        except Exception as e:
            # Only add error if it's not the common "not found" error
            if not "not found" in str(e) and not "cannot find" in str(e).lower():
                exif_data["EXIFTOOL_ERROR"] = str(e)
    
    # Method 5: Using external exiftool command if installed
    if exiftool_path:
        try:
            # Use the provided exiftool path with a timeout to avoid hangs
            result = subprocess.run(
                [exiftool_path, "-j", "-a", "-u", "-G1", image_path],
                capture_output=True, text=True, timeout=30, check=False
            )
            if result.returncode == 0:
                try:
                    exiftool_json = json.loads(result.stdout)
                    if exiftool_json and len(exiftool_json) > 0:
                        for key, value in exiftool_json[0].items():
                            # Clean up tag name
                            clean_key = key.replace(":", "_").replace(" ", "_")
                            exif_data[f"EXIFTOOL_CMD_{clean_key}"] = value
                            
                            # Look specifically for profile date time
                            if "profile" in key.lower() and ("date" in key.lower() or "time" in key.lower()):
                                exif_data["PROFILE_DATE_TIME"] = value
                except json.JSONDecodeError:
                    # If JSON parsing fails, try regular format
                    try:
                        # Run again with regular format
                        plain_result = subprocess.run(
                            [exiftool_path, "-a", "-u", "-G1", image_path],
                            capture_output=True, text=True, timeout=15, check=False
                        )
                        
                        if plain_result.returncode == 0:
                            # Process raw output
                            for line in plain_result.stdout.splitlines():
                                if ":" in line:
                                    parts = line.split(":", 1)
                                    if len(parts) == 2:
                                        key = parts[0].strip().replace(" ", "_")
                                        value = parts[1].strip()
                                        exif_data[f"EXIFTOOL_RAW_{key}"] = value
                                        
                                        # Look specifically for profile date time
                                        if "profile" in key.lower() and ("date" in key.lower() or "time" in key.lower()):
                                            exif_data["PROFILE_DATE_TIME"] = value
                    except Exception as e:
                        exif_data["EXIFTOOL_PLAIN_ERROR"] = str(e)
        except subprocess.TimeoutExpired:
            exif_data["EXIFTOOL_TIMEOUT"] = "ExifTool command timed out after 30 seconds"
        except Exception as e:
            # Don't add error message if exiftool simply isn't installed
            if not "not found" in str(e) and not "cannot find" in str(e).lower():
                exif_data["EXIFTOOL_CMD_ERROR"] = str(e)
    
    # Additional checks for raw binary data that might contain profile date/time
    try:
        with open(image_path, 'rb') as f:
            raw_data = f.read()
            # Look for common date format patterns in binary data
            date_pattern = re.compile(b'profile[_\\s]date[_\\s]time[\\s:\\=]+([^\\x00-\\x1F]{8,25})', re.IGNORECASE)
            match = date_pattern.search(raw_data)
            if match:
                try:
                    decoded = match.group(1).decode('utf-8', errors='replace')
                    exif_data["RAW_PROFILE_DATE_TIME"] = decoded
                except:
                    pass
    except Exception as e:
        exif_data["RAW_SEARCH_ERROR"] = str(e)
    
    return exif_data


def format_exif_data(exif_data):
    """Format EXIF data for text file output with proper indentation and formatting."""
    result = []
    result.append("=" * 80)
    result.append(f"EXIF Data Extraction - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    result.append("=" * 80)
    result.append("")
    
    # Process and sort the exif data by categories
    categories = {}
    
    for key, value in sorted(exif_data.items()):
        # Determine category from key prefix
        if "_" in key:
            cat = key.split("_")[0]
        else:
            cat = "Other"
        
        if cat not in categories:
            categories[cat] = []
        
        # Format the value for better readability
        if isinstance(value, bytes):
            try:
                formatted_value = value.decode('utf-8', errors='replace')
            except:
                formatted_value = f"<binary data: {len(value)} bytes>"
        elif isinstance(value, (tuple, list)) and len(value) > 5:
            formatted_value = f"{str(value[:5])[:-1]}, ... (total items: {len(value)}))"
        else:
            formatted_value = str(value)
        
        categories[cat].append((key, formatted_value))
    
    # Print data by category
    for cat in sorted(categories.keys()):
        result.append(f"[{cat}]")
        result.append("-" * 80)
        
        for key, value in categories[cat]:
            # Handle multiline values
            if "\n" in str(value):
                result.append(f"{key}:")
                for line in str(value).split("\n"):
                    result.append(f"    {line}")
            else:
                result.append(f"{key}: {value}")
        
        result.append("")
    
    return "\n".join(result)


def process_folder(folder_path):
    """Process all images in a folder and extract their EXIF data."""
    print(f"Processing images in folder: {folder_path}")
    
    # Check if folder exists
    if not os.path.isdir(folder_path):
        print(f"Error: The folder '{folder_path}' does not exist.")
        return
    
    # Get all files in the folder
    files = os.listdir(folder_path)
    
    # Count variables
    total_files = 0
    processed_files = 0
    
    # Supported image extensions
    image_extensions = ('.jpg', '.jpeg', '.tiff', '.tif', '.png', '.bmp', '.heic', '.heif', '.nef', '.cr2', '.arw')
    
    # Check for ExifTool availability and save path if found
    exiftool_path = None
    
    # First check for a direct path in recently installed location
    direct_exiftool_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), "ExifTool", "exiftool.exe")
    if os.path.exists(direct_exiftool_path):
        try:
            result = subprocess.run([direct_exiftool_path, "-ver"], 
                                  capture_output=True, text=True, timeout=5, check=False)
            if result.returncode == 0:
                exiftool_path = direct_exiftool_path
                print(f"ExifTool found at: {exiftool_path}")
                print(f"ExifTool version: {result.stdout.strip()}")
        except Exception as e:
            print(f"Error testing ExifTool at {direct_exiftool_path}: {e}")
    
    # If direct path didn't work, try other locations
    if not exiftool_path:
        exiftool_locations = [
            "exiftool",  # If in PATH
            os.path.join(os.environ.get('PROGRAMFILES', 'C:\\Program Files'), "ExifTool", "exiftool.exe"),
            os.path.join(os.environ.get('USERPROFILE', ''), "ExifTool", "exiftool.exe")
        ]
        
        for location in exiftool_locations:
            try:
                result = subprocess.run([location, "-ver"], 
                                      capture_output=True, text=True, timeout=5, check=False)
                if result.returncode == 0:
                    exiftool_path = location
                    print(f"ExifTool found at: {exiftool_path}")
                    print(f"ExifTool version: {result.stdout.strip()}")
                    break
            except:
                continue
    
    if not exiftool_path:
        print("Warning: ExifTool command line utility not found.")
        print("For most complete extraction (including profile_date_time), install ExifTool from: https://exiftool.org/")
        print("Continuing with available extraction methods...\n")
    
    # Check for PyExifTool availability
    if not exiftool:
        print("Note: PyExifTool module not available. Consider installing for better extraction:")
        print("pip install PyExifTool\n")
    
    # Check for ExifRead availability
    if not exifread:
        print("Note: ExifRead module not available. Consider installing for better extraction:")
        print("pip install ExifRead\n")
        
    for filename in files:
        total_files += 1
        file_path = os.path.join(folder_path, filename)
        
        # Skip if not a file
        if not os.path.isfile(file_path):
            continue
        
        # Check if it's an image file
        if not filename.lower().endswith(image_extensions):
            continue
        
        try:
            print(f"Processing: {filename}")
            
            # Extract EXIF data
            exif_data = extract_all_exif(file_path, exiftool_path)
            
            # Specifically check for profile_date_time
            has_profile_date = False
            for key in exif_data:
                if "profile" in key.lower() and ("date" in key.lower() or "time" in key.lower()):
                    has_profile_date = True
                    print(f"  Found profile date/time: {key} = {exif_data[key]}")
                    break
                    
            if not has_profile_date:
                print(f"  Note: No profile_date_time found in {filename}")
            
            # Format the EXIF data for output
            formatted_data = format_exif_data(exif_data)
            
            # Create output filename (same as original but with .txt extension)
            base_name = os.path.splitext(filename)[0]
            output_file = os.path.join(folder_path, f"{base_name}.txt")
            
            # Write to output file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_data)
            
            processed_files += 1
            print(f"  EXIF data saved to: {output_file}")
            print(f"  Total EXIF tags found: {len(exif_data)}")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    print(f"\nSummary: Processed {processed_files} of {total_files} files in the folder.")
    if processed_files > 0:
        print("Important Notes:")
        print("1. If certain EXIF fields are missing (like profile_date_time), consider installing ExifTool")
        print("   from https://exiftool.org/ for more complete extraction capability.")
        print("2. Run the script with --install-deps to install recommended Python libraries.")
        print("3. Some proprietary or uncommon metadata may require specific tools for extraction.")


def install_exiftool_windows():
    """Download and install ExifTool on Windows."""
    import tempfile
    import zipfile
    import shutil
    import ctypes
    import winreg
    from urllib.request import urlretrieve, urlopen
    import re
    import ssl
    
    print("Installing ExifTool for Windows...")
    
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "exiftool.zip")
    
    try:
        # Use the specific URL you provided
        exiftool_url = "https://exiftool.org/exiftool-13.27_64.zip"
        print(f"Downloading ExifTool from: {exiftool_url}")
        
        # Create SSL context that ignores certificate validation
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        # Download with robust error handling
        try:
            with urlopen(exiftool_url, context=ctx) as response:
                with open(zip_path, 'wb') as out_file:
                    shutil.copyfileobj(response, out_file)
                    
            # Check if download was successful
            if not os.path.exists(zip_path) or os.path.getsize(zip_path) < 1000:
                raise Exception("Downloaded file is invalid or empty")
                
        except Exception as e:
            print(f"Error downloading from {exiftool_url}: {e}")
            print("Trying alternative download methods...")
            
            # Try urlretrieve as an alternative
            try:
                urlretrieve(exiftool_url, zip_path)
            except Exception as e2:
                print(f"urlretrieve also failed: {e2}")
                
                # Try a backup URL
                backup_url = "https://exiftool.org/exiftool-13.27.zip"
                print(f"Trying backup URL: {backup_url}")
                try:
                    with urlopen(backup_url, context=ctx) as response:
                        with open(zip_path, 'wb') as out_file:
                            shutil.copyfileobj(response, out_file)
                except Exception as e3:
                    print(f"All download attempts failed. Last error: {e3}")
                    return False
            
        # Check if download was successful
        if not os.path.exists(zip_path) or os.path.getsize(zip_path) < 1000:
            print("Error: Downloaded file is invalid or empty.")
            return False
            
        # Extract zip file
        print("Extracting files...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        # Find the exiftool(-k).exe file
        exiftool_exe = None
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.startswith("exiftool") and file.endswith(".exe"):
                    exiftool_exe = os.path.join(root, file)
                    break
            if exiftool_exe:
                break
        
        if not exiftool_exe:
            print("Error: ExifTool executable not found in the downloaded package.")
            print("Contents of the extracted directory:")
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    print(f"  {os.path.join(root, file)}")
            return False
        
        # Determine installation path
        # Try to get Program Files path
        try:
            program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
            exiftool_dir = os.path.join(program_files, "ExifTool")
            
            # Check if we have admin privileges to install to Program Files
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except:
                is_admin = False
                
            # If not admin, use AppData folder instead
            if not is_admin:
                local_appdata = os.environ.get('LOCALAPPDATA', '')
                if local_appdata:
                    exiftool_dir = os.path.join(local_appdata, "ExifTool")
                else:
                    user_profile = os.environ.get('USERPROFILE', '')
                    if user_profile:
                        exiftool_dir = os.path.join(user_profile, "ExifTool")
                    else:
                        # Last resort: use temp directory
                        exiftool_dir = os.path.join(temp_dir, "ExifTool")
        except:
            # If any error, use Documents folder
            user_profile = os.environ.get('USERPROFILE', '')
            if user_profile:
                exiftool_dir = os.path.join(user_profile, "ExifTool")
            else:
                exiftool_dir = os.path.join(temp_dir, "ExifTool")
        
        # Create directory if it doesn't exist
        os.makedirs(exiftool_dir, exist_ok=True)
        
        # Rename and copy the file
        exiftool_target = os.path.join(exiftool_dir, "exiftool.exe")
        shutil.copy2(exiftool_exe, exiftool_target)
        
        print(f"ExifTool installed to: {exiftool_dir}")
        
        # Add to PATH (requires admin privileges, so we'll just provide instructions if not admin)
        path_updated = False
        try:
            if ctypes.windll.shell32.IsUserAnAdmin() != 0:
                # Get current PATH
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 0, winreg.KEY_ALL_ACCESS)
                path = winreg.QueryValueEx(key, 'Path')[0]
                
                if exiftool_dir not in path:
                    # Update PATH
                    new_path = path + ';' + exiftool_dir
                    winreg.SetValueEx(key, 'Path', 0, winreg.REG_EXPAND_SZ, new_path)
                    winreg.CloseKey(key)
                    path_updated = True
                    
                    # Broadcast environment change
                    try:
                        import win32con
                        import win32gui
                        win32gui.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')
                    except ImportError:
                        pass
        except:
            path_updated = False
        
        # If PATH wasn't updated, set a temporary environment variable
        if not path_updated:
            os.environ['PATH'] = os.environ.get('PATH', '') + ';' + exiftool_dir
            print(f"Note: ExifTool has been installed but not added to your system PATH.")
            print(f"To use ExifTool outside this script, add this directory to your PATH:")
            print(f"  {exiftool_dir}")
            print(f"Or create a batch file to run this script with the correct PATH.")
        
        # Test installation
        try:
            subprocess.run([os.path.join(exiftool_dir, "exiftool.exe"), "-ver"], 
                          capture_output=True, check=True)
            print("ExifTool installation successful!")
            return True
        except:
            print("Warning: ExifTool installation appears to have issues.")
            print(f"Try running: {os.path.join(exiftool_dir, 'exiftool.exe')} -ver")
            return False
            
    except Exception as e:
        print(f"Error installing ExifTool: {e}")
        return False
    finally:
        # Clean up temp files, except the exiftool directory if it's inside temp
        try:
            if temp_dir != exiftool_dir and not exiftool_dir.startswith(temp_dir):
                shutil.rmtree(temp_dir)
        except:
            pass
    
    return False


def main():
    parser = argparse.ArgumentParser(description='Extract all available EXIF data from images in a folder.')
    parser.add_argument('folder', help='Path to the folder containing images')
    parser.add_argument('--install-deps', action='store_true', help='Install recommended dependencies for maximum EXIF extraction')
    parser.add_argument('--install-exiftool', action='store_true', help='Download and install ExifTool (Windows only)')
    
    args = parser.parse_args()
    
    # Install ExifTool if requested (Windows only)
    if args.install_exiftool:
        if os.name == 'nt':  # Windows
            try:
                install_exiftool_windows()
            except Exception as e:
                print(f"Error during ExifTool installation: {e}")
                print("You can download and install ExifTool manually from: https://exiftool.org/")
        else:
            print("Automatic ExifTool installation is only available on Windows.")
            print("For other platforms, please install ExifTool using your package manager:")
            print("  - macOS: 'brew install exiftool'")
            print("  - Linux: 'apt-get install libimage-exiftool-perl' or equivalent")
    
    # Install Python dependencies if requested
    if args.install_deps:
        print("Installing recommended Python dependencies for maximum EXIF extraction...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow", "piexif", "ExifRead", "PyExifTool"])
            print("Python dependencies installed successfully!")
        except Exception as e:
            print(f"Error installing Python dependencies: {e}")
            print("You may need to install them manually:")
            print("pip install Pillow piexif ExifRead PyExifTool")
    
    process_folder(args.folder)


if __name__ == "__main__":
    # Add a quick check to see if we're on Windows and offer ExifTool installation
    if os.name == 'nt' and '--install-exiftool' not in sys.argv and '--help' not in sys.argv:
        try:
            # Check if ExifTool is already installed
            subprocess.run(["exiftool", "-ver"], capture_output=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            print("\nExifTool not detected on your Windows system.")
            print("ExifTool provides the most comprehensive EXIF extraction (including profile_date_time).")
            response = input("Would you like to install ExifTool automatically? (y/n): ")
            if response.lower().startswith('y'):
                try:
                    install_exiftool_windows()
                except Exception as e:
                    print(f"Error during ExifTool installation: {e}")
                    print("You can download and install ExifTool manually from: https://exiftool.org/")
            
    main()
