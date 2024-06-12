from PIL import Image
from tensorflow.keras.applications.mobilenet import MobileNet
from tensorflow.keras.applications.mobilenet import preprocess_input, decode_predictions
import numpy as np


def classifierMobileNet(img_path, tope):
    model = MobileNet()  # model de image net
    img = np.asarray(Image.open(img_path))  # image de l'entree ou bien de produit choisit
    img = resize(img, [224, 224])  # redimensionner l'image a 224*224
    X = np.reshape(img, [1, 224, 224, 3])  # redemensionner
    preds = model.predict(X)  # predir des resultats
    produits_predits = decode_predictions(preds, top=tope)
    return produits_predits


print("hello world")
