# 🚁 AI-Based UAV / Drone Detection and Surveillance System

# 📌 Project Overview

This project presents a complete **AI-powered UAV (Drone) Detection and Surveillance System** capable of detecting multiple UAV categories from **images, videos, and live webcam streams**.

The system combines **YOLOv8**, **Faster R-CNN**, and **SSD** object detection models, performs comparative performance analysis, and deploys the best-performing model using a modern Flask web application.

The repository contains the complete source code, Jupyter notebooks, evaluation reports, deployment application, and documentation. Large datasets, trained models, and videos are provided separately through Google Drive because of GitHub file size limitations.

---

# ✨ Features

* 🚁 UAV Detection using YOLOv8
* 📷 Image Detection
* 🎥 Video Detection
* 📹 Live Webcam Detection
* 🔊 Voice Alert
* 🚨 Siren Alert
* 📧 Email Notification
* 📊 Detection History
* 📈 Model Comparison Dashboard
* 📄 PDF & Excel Report Generation
* 🗂 Dataset Analysis
* 📑 Detection Statistics
* 💾 SQLite Database Integration
* 🌐 Flask Web Dashboard

---

# 📂 Repository Structure

```text
Drone_Detection/
│
├── AI_UAV_Surveillance/
│   ├── app.py
│   ├── config.py
│   ├── database/
│   ├── modules/
│   ├── static/
│   ├── templates/
│   └── models/
│
├── YOLOv8_End_to_End.ipynb
├── FasterRCNN_End_to_End.ipynb
├── SSD_End_to_End.ipynb
├── Model_Comparison_Analysis.ipynb
│
├── reports/
├── runs/
├── test_images/
├── requirements.txt
├── README.md
└── .gitignore
```

---

# 📥 Download Large Files

The following folders are hosted on Google Drive.

| Folder            | Download                                                                             |
| ----------------- | ------------------------------------------------------------------------------------ |
| data              | https://drive.google.com/drive/folders/1lnlCq4T6IG8wQpKSOfN_q9CoAja_r9XI?usp=sharing |
| output_recording  | https://drive.google.com/drive/folders/1n5CVxtzzaG_y-THziRaPZrXRQ6mnP3kY?usp=sharing |
| processed_dataset | https://drive.google.com/drive/folders/1esHUtHPSfPLeCk_az-oGFj4DpKYZXqk6?usp=sharing |
| test_video        | https://drive.google.com/drive/folders/1kevSACw-HzjM8A4nVoxnTRiLuPhXyJw_?usp=sharing |
| trained_models    | https://drive.google.com/drive/folders/13ETLVFw7_Elt-UH5QYOsNfd3w98G_QnU?usp=sharing |

After downloading, keep the folder names unchanged and place them in the project root.

---

# 📊 Dataset Summary

| Property          |     Value |
| ----------------- | --------: |
| Total Images      |    16,298 |
| Total Annotations |    17,658 |
| Training Images   |    13,661 |
| Validation Images |     2,637 |
| Image Resolution  | 640 × 640 |

### Classes

| ID | Class              |
| -: | ------------------ |
|  0 | UAV                |
|  1 | Side-by-Side Rotor |
|  2 | Single Rotor       |
|  3 | Tandem Rotor       |

---

# 🤖 Model Performance

| Model        | Precision | Recall | F1 Score |  mAP50 |   FPS |
| ------------ | --------: | -----: | -------: | -----: | ----: |
| YOLOv8       |    0.9487 | 0.9120 |   0.9300 | 0.9471 | 51.55 |
| SSD          |    0.7120 | 0.6953 |   0.7036 | 0.7120 | 48.16 |
| Faster R-CNN |    0.4364 | 0.7500 |   0.5517 | 0.4364 | 37.06 |

**Selected Deployment Model:** **YOLOv8**

Reasons:

* Highest Precision
* Highest mAP
* Best Detection Speed
* Best Real-Time Performance
* Small Model Size

---

# 💻 System Requirements

* Windows 10 / 11
* Python 3.10+
* CUDA (Optional)
* NVIDIA GPU (Recommended)
* PyTorch
* OpenCV
* Flask
* Ultralytics

---

# ⚙ Installation

```bash
git clone https://github.com/YOUR_USERNAME/Drone_Detection.git

cd Drone_Detection

python -m venv .venv

.venv\Scripts\activate

pip install -r requirements.txt
```

Download the large folders from Google Drive and place them inside the project directory.

---

# 🚀 Run the Flask Application

```bash
cd AI_UAV_Surveillance

python app.py
```

Open

```
http://localhost:5000
```

Default Login

```
Username : admin

Password : admin123
```

---

# 📒 Notebook Execution Order

1. YOLOv8_End_to_End.ipynb

2. FasterRCNN_End_to_End.ipynb

3. SSD_End_to_End.ipynb

4. Model_Comparison_Analysis.ipynb

---

# 📁 Generated Outputs

The notebooks automatically generate

* reports/
* runs/
* trained_models/
* processed_dataset/

The **reports** and **runs** folders are included in this repository.

Large folders such as **trained_models**, **processed_dataset**, **data**, and **videos** should be downloaded from Google Drive.

---

# 🌐 Flask Application Features

* Dashboard
* Image Detection
* Video Detection
* Webcam Detection
* Detection History
* Report Generation
* Voice Alerts
* Siren Alerts
* Email Alerts
* Detection Statistics
* SQLite Database

---

# 📌 Important Notes

* GitHub does **not** contain datasets or trained models.
* Download the required folders using the Google Drive links above.
* Do **not** rename any downloaded folders.
* Place them in the project root before running the notebooks or Flask application.
* YOLOv8 is the final deployment model used by the surveillance system.

---

# ⭐ Support

If you found this project useful, please consider giving it a ⭐ on GitHub.
