## 🌱 Zarkhez

**Zarkhez** is a scalable, modular precision agriculture platform.
It currently offers:

* **NDVI-based field analysis** using Sentinel Hub satellite data.
* **Crop disease detection** with AI-powered computer vision, including corrective measures via curated videos.

More features (e.g., irrigation recommendations, soil health analysis) are planned in future phases.

---

## 📦 Project Structure

```plaintext
zarkhez/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers (e.g., ndvi, disease)
│   │   ├── services/     # Business logic & external integrations
│   │   ├── models/       # Pydantic schemas
│   │   ├── core/         # Config, utilities, constants
│   │   └── tmp/          # Temp files (e.g., downloaded satellite images)
│   ├── tests/            # Unit & integration tests
│   └── requirements.txt  # Python dependencies
├── frontend/             # Planned: React / Vue / Flutter frontend
└── README.md
```

✅ *Designed for scalability: add new modules easily by adding routers & services.*

---

## ⚙️ Features

✅ **NDVI Field Analysis**

* Uses Sentinel Hub API
* Computes vegetation indices
* Generates heatmaps & trends over time

✅ **Crop Disease Detection**

* AI/ML model detects diseases from crop images
* Returns curated preventive/corrective YouTube videos

📈 *Phase 2 & beyond: irrigation recommendations, soil health reports, yield prediction.*

---

## 🚀 Getting Started

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

> Make sure to set your environment variables (e.g., Sentinel Hub credentials).

### Frontend

Planned (React / Vue / Flutter): will be integrated with the backend APIs.

---

## 🧪 Testing

```bash
cd backend
pytest
```

---

## 🛠 Tech Stack

* **FastAPI** – backend & APIs
* **Pydantic** – data validation
* **Sentinel Hub** – satellite data
* **Custom ML models** – crop disease detection
* Planned: **React** / **Vue** / **Flutter** frontend

---

## 📌 Contributing

1. Fork this repo
2. Create a new feature branch
3. Commit changes
4. Open a PR

We welcome PRs that improve modularity, add tests, or extend features! 🌾

---

## 📄 License

MIT License — see `LICENSE` for details.
