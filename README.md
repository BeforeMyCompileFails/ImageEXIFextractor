# EXIF Data Extractor

**EXIF Data Extractor** is a powerful Python tool that extracts **all available EXIF and metadata** from image files in a folder using multiple methods. It supports popular libraries and even system-installed utilities to ensure maximum extraction depth. Each image’s metadata is saved in a well-organized `.txt` file named after the original image.

Created by **Denis (@BeforeMyCompileFails), 2025**

---

## 📆 Features

- ✅ **Multi-method extraction** for thorough coverage:
  - PIL (Pillow)
  - Piexif
  - ExifRead (if installed)
  - ExifTool command-line (if available)
- 📂 **Processes all images in a folder**
- 📄 **Outputs metadata** into per-image `.txt` files with nicely formatted and categorized content
- 🔍 **Searches for ICC profile date/time**, including inside raw binary data
- ⚖ Optional auto-install of:
  - Python dependencies: `Pillow`, `piexif`, `ExifRead`, `PyExifTool`
  - ExifTool for Windows
- 📷 Supports major image formats: `.jpg`, `.jpeg`, `.tiff`, `.png`, `.bmp`, `.heic`, `.nef`, `.cr2`, `.arw`, and more

---

## 🚀 Usage

### Basic usage:
```bash
python exif_extractor.py /path/to/image/folder
```

### With dependency installation:
```bash
python exif_extractor.py /path/to/image/folder --install-deps
```

### On Windows - install ExifTool automatically:
```bash
python exif_extractor.py /path/to/image/folder --install-exiftool
```

---

## 📝 Output

For every image, a `.txt` file will be generated containing its EXIF data, grouped and formatted like:

```
================================================================================
EXIF Data Extraction - 2025-04-24 16:35:00
================================================================================

[FILE]
--------------------------------------------------------------------------------
FILE_NAME: example.jpg
FILE_SIZE: 153248
FILE_CREATED: 2025-04-20 12:10:05
...

[Exif]
--------------------------------------------------------------------------------
Exif_DateTimeOriginal: 2024:12:31 23:59:59
Exif_Make: Canon
Exif_Model: EOS R5
...

[ICC]
--------------------------------------------------------------------------------
ICC_PROFILE_DATE: 2024-12-31
ICC_PROFILE_TIME: 23:59:59
...
```

---

## 🛠 Recommended Setup

Install Python libraries:
```bash
pip install Pillow piexif ExifRead PyExifTool
```

Install [ExifTool](https://exiftool.org/) manually or use the `--install-exiftool` flag on Windows.

---

## 🔍 Tip

For the most complete metadata (especially `profile_date_time`), having **ExifTool** installed is highly recommended.

---

## 📂 Supported Formats

JPEG, TIFF, PNG, BMP, HEIC, HEIF, NEF, CR2, ARW, and other common photo formats.

---

## 📄 License

MIT License. Use freely and modify as needed.

