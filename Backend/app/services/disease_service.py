import tensorflow as tf # type: ignore
import numpy as np
from app.core.config import settings  # type: ignore
from tensorflow.keras.preprocessing import image # type: ignore
import os
import io

# Load model once at startup
model = tf.keras.models.load_model(settings.disease_model_path)

# Class labels
class_labels = [
    'Black Rust', 'Blast', 'Brown Rust', 'Fusarium Head Blight', 'Healthy Wheat',
    'Leaf Blight', 'Mildew', 'Mite', 'Septoria', 'Smut',
    'Stem fly', 'Tan spot', 'Yellow Rust'
]

def predict_disease(image_bytes) -> str:
    # Read from bytes instead of path
    img = image.load_img(io.BytesIO(image_bytes), target_size=(128, 128))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)

    prediction = model.predict(img_array)
    predicted_class = class_labels[np.argmax(prediction)]
    return predicted_class
