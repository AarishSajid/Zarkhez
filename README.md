# 🌾 Zarkhez

**Zarkhez** is an AI-powered web app designed for farmers to better monitor and manage their fields.  
It combines two core modules (built for scalability):

- 🛰 **Field Analysis**: Uses satellite imagery (Sentinel Hub) to compute NDVI, show vegetation health trends, and render true-color & heatmap images.
- 🤖 **Crop Disease Detection**: (Coming next) A computer vision module to detect crop diseases from images and provide corrective measures via video guides.

All features are built as separate API routers, making it easy to extend or add new modules.

---

## 🛠 **Project structure** (current & planned)

zarkhez/
├── backend/
│ ├── app/
│ │ ├── apis/ ← FastAPI routers (ndvi_api.py, disease_api.py, etc.)
│ │ ├── models/ ← Pydantic request/response models
│ │ ├── services/ ← Core service logic (NDVI, disease detection)
│ │ └── tmp/ ← Temp folder for downloaded satellite images
│ ├── main.py ← FastAPI entry point
│ └── requirements.txt
├── frontend/ ← Planned: React / Vue / Flutter web frontend
└── README.md


> ✅ **Design for scalability**: new features (e.g., soil moisture analysis) can be added by adding new service + router.

---

## 🚀 **Current API features** (Phase 1)

✅ NDVI analysis:
- `/api/v1/ndvi/analyze`: Calculate NDVI & get vegetation health
- `/api/v1/ndvi/heatmap`: NDVI heatmap with cloud masking
- `/api/v1/ndvi/image`: True color satellite image
- `/api/v1/ndvi/history`: NDVI trend over recent weeks

All endpoints are modular and documented via Swagger UI.

---

## 🧪 **Running locally (backend only)**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```
Then open docs:

http://127.0.0.1:8000/docs
