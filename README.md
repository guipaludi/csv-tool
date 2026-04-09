# 📦 CSV Tool

A lightweight data extraction tool that converts JSON files into CSV format, supporting uploads of folders and compressed files (ZIP), including nested archives.

---

## 🚀 Features

* 📁 Upload ZIP files (including nested ZIPs)
* 🔍 Search for specific terms inside JSON content
* 🧠 Case-insensitive search
* 📊 Extract custom fields dynamically
* 🧾 Generate CSV files instantly
* 🔄 Handles complex folder structures automatically

---

## 🛠️ Tech Stack

* Python
* Streamlit
* Pandas

---

## ▶️ How to Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## 🌐 Usage

1. Upload a ZIP file containing JSON exports
2. (Optional) Enter a search term
3. (Optional) Enter fields to extract
4. Click **Generate CSV**
5. Download the result

---

## 📦 Supported Input

* JSON files in any folder structure
* ZIP files
* Nested ZIP files (ZIP inside ZIP)

---

## ⚠️ Notes

* Large files may take longer to process
* The app runs fully in-memory (no data is stored)

---

## 📄 License

MIT License

---

## 👨‍💻 Author

Built by Guilherme Paludi
