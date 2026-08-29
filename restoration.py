"""
Module de restauration de photos.
Utilise GFPGAN pour les visages et Real-ESRGAN pour la super-résolution.
Les modèles sont téléchargés automatiquement au premier lancement.
"""

import io
import os
import cv2
import numpy as np
from PIL import Image

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
os.makedirs(MODEL_DIR, exist_ok=True)


def full_restoration(image_bytes: bytes) -> bytes:
    """Pipeline complet : GFPGAN (visages) + Real-ESRGAN (super-résolution)."""
    img_array = _bytes_to_cv2(image_bytes)

    # Étape 1 — Restauration des visages avec GFPGAN
    img_array = restore_faces(img_array)

    # Étape 2 — Super-résolution avec Real-ESRGAN
    img_array = upscale(img_array)

    # Étape 3 — Post-traitement léger
    img_array = post_process(img_array)

    return _cv2_to_bytes(img_array)


# ── GFPGAN (restauration visages) ─────────────────────────────────────────────
def restore_faces(img: np.ndarray) -> np.ndarray:
    try:
        from gfpgan import GFPGANer

        model_path = os.path.join(MODEL_DIR, "GFPGANv1.4.pth")
        if not os.path.exists(model_path):
            _download_model(
                "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth",
                model_path
            )

        restorer = GFPGANer(
            model_path=model_path,
            upscale=1,
            arch="clean",
            channel_multiplier=2,
            bg_upsampler=None
        )
        _, _, output = restorer.enhance(
            img,
            has_aligned=False,
            only_center_face=False,
            paste_back=True
        )
        print("GFPGAN appliqué avec succès")
        return output

    except Exception as e:
        print(f"GFPGAN non disponible ({e}), étape ignorée")
        return img


# ── Real-ESRGAN (super-résolution) ────────────────────────────────────────────
def upscale(img: np.ndarray, scale: int = 2) -> np.ndarray:
    try:
        from basicsr.archs.rrdbnet_arch import RRDBNet
        from realesrgan import RealESRGANer

        model_path = os.path.join(MODEL_DIR, "RealESRGAN_x4plus.pth")
        if not os.path.exists(model_path):
            _download_model(
                "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
                model_path
            )

        model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                        num_block=23, num_grow_ch=32, scale=4)
        upsampler = RealESRGANer(
            scale=4,
            model_path=model_path,
            model=model,
            tile=400,
            tile_pad=10,
            pre_pad=0,
            half=False
        )
        output, _ = upsampler.enhance(img, outscale=scale)
        print(f"Real-ESRGAN appliqué (x{scale})")
        return output

    except Exception as e:
        print(f"Real-ESRGAN non disponible ({e}), étape ignorée")
        return img


# ── Post-traitement ────────────────────────────────────────────────────────────
def post_process(img: np.ndarray) -> np.ndarray:
    """Netteté légère et débruitage final."""
    # Débruitage doux
    img = cv2.fastNlMeansDenoisingColored(img, None, 3, 3, 7, 21)
    # Légère netteté
    kernel = np.array([[0, -0.3, 0], [-0.3, 2.2, -0.3], [0, -0.3, 0]])
    img = cv2.filter2D(img, -1, kernel)
    return img


# ── Utilitaires ────────────────────────────────────────────────────────────────
def _bytes_to_cv2(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    return img


def _cv2_to_bytes(img: np.ndarray) -> bytes:
    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return buf.tobytes()


def _download_model(url: str, dest: str):
    import urllib.request
    print(f"Téléchargement du modèle : {os.path.basename(dest)} ...")
    urllib.request.urlretrieve(url, dest)
    print("Téléchargement terminé.")
