"""Pipeline de percepcion del prototipo P2 (descartable).

YOLO11n ONNX (CPU) + MediaPipe HandLandmarker (Tasks API) + gestos por reglas.
Stack segun research R2: onnxruntime 1.29.0, opencv-python 4.14, mediapipe 1.0.1.
"""

import time
from pathlib import Path

import cv2
import numpy as np
from gestos import clasificar_gesto

MODELOS = Path(__file__).resolve().parent / "models"

CONF = 0.25
IOU = 0.7
IMGSZ = 640

CLASES_COCO = [
    "persona",
    "bicicleta",
    "auto",
    "moto",
    "avion",
    "bus",
    "tren",
    "camion",
    "bote",
    "semaforo",
    "hidrante",
    "señal de alto",
    "parquimetro",
    "banco",
    "pajaro",
    "gato",
    "perro",
    "caballo",
    "oveja",
    "vaca",
    "elefante",
    "oso",
    "cebra",
    "jirafa",
    "mochila",
    "paraguas",
    "cartera",
    "corbata",
    "maleta",
    "frisbee",
    "esquis",
    "snowboard",
    "pelota",
    "cometa",
    "bate",
    "guante de beisbol",
    "skateboard",
    "tabla de surf",
    "raqueta",
    "botella",
    "copa",
    "taza",
    "tenedor",
    "cuchillo",
    "cuchara",
    "bol",
    "banana",
    "manzana",
    "sandwich",
    "naranja",
    "brocoli",
    "zanahoria",
    "pancho",
    "pizza",
    "donut",
    "torta",
    "silla",
    "sofa",
    "maceta",
    "cama",
    "mesa de comedor",
    "inodoro",
    "tv",
    "laptop",
    "mouse",
    "control remoto",
    "teclado",
    "celular",
    "microondas",
    "horno",
    "tostadora",
    "lavabo",
    "refrigerador",
    "libro",
    "reloj",
    "florero",
    "tijera",
    "oso de peluche",
    "secador",
    "cepillo de dientes",
]


class Letterbox:
    def __init__(self, size=IMGSZ, stride=32, padding=114):
        self.size = size
        self.stride = stride
        self.padding = padding

    def __call__(self, img):
        h, w = img.shape[:2]
        r = min(self.size / h, self.size / w)
        nw, nh = round(w * r), round(h * r)
        dw = (self.size - nw) % self.stride
        dh = (self.size - nh) % self.stride
        top, bottom = dh // 2, dh - dh // 2
        left, right = dw // 2, dw - dw // 2
        scaled = cv2.resize(img, (nw, nh), interpolation=cv2.INTER_LINEAR)
        padded = cv2.copyMakeBorder(
            scaled,
            top,
            bottom,
            left,
            right,
            cv2.BORDER_CONSTANT,
            value=(self.padding, self.padding, self.padding),
        )
        return padded, r, (left, top)


class YoloDetector:
    def __init__(self, path, conf=CONF, iou=IOU):
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        self.sess = ort.InferenceSession(
            str(path), sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self.conf = conf
        self.iou = iou
        self.letterbox = Letterbox()

    def detectar(self, frame_bgr):
        padded, r, (px, py) = self.letterbox(frame_bgr)
        blob = padded[:, :, ::-1].astype(np.float32) / 255.0
        blob = np.transpose(blob, (2, 0, 1))[None]
        out = self.sess.run(None, {self.sess.get_inputs()[0].name: blob})[0]
        out = out[0].T  # (8400, 84)
        boxes, scores = out[:, :4], out[:, 4:]
        cls = scores.argmax(axis=1)
        score = scores.max(axis=1)
        keep = score >= self.conf
        boxes, cls, score = boxes[keep], cls[keep], score[keep]
        if not boxes.shape[0]:
            return []
        cx, cy, w, h = boxes.T
        x1 = (cx - w / 2 - px) / r
        y1 = (cy - h / 2 - py) / r
        x2 = (cx + w / 2 - px) / r
        y2 = (cy + h / 2 - py) / r
        dets = np.stack([x1, y1, x2, y2, score, cls.astype(float)], axis=1)
        idx = self._nms(dets, self.iou)
        return [
            {
                "x1": float(d[0]),
                "y1": float(d[1]),
                "x2": float(d[2]),
                "y2": float(d[3]),
                "conf": float(d[4]),
                "clase": int(d[5]),
                "etiqueta": CLASES_COCO[int(d[5])],
            }
            for d in dets[idx]
        ]

    @staticmethod
    def _nms(dets, iou_thr=IOU):
        x1, y1, x2, y2 = dets[:, 0], dets[:, 1], dets[:, 2], dets[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = np.argsort(dets[:, 4])[::-1]
        keep = []
        while order.size:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0, xx2 - xx1) * np.maximum(0, yy2 - yy1)
            union = areas[i] + areas[order[1:]] - inter
            ovr = inter / np.maximum(union, 1e-9)
            order = order[1:][ovr <= iou_thr]
        return keep


class Mano:
    def __init__(self, path):
        import mediapipe as mp

        base = mp.tasks.BaseOptions(model_asset_path=str(path))
        opts = mp.tasks.vision.HandLandmarkerOptions(
            base_options=base,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_hand_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=mp.tasks.vision.RunningMode.VIDEO,
        )
        self.landmarker = mp.tasks.vision.HandLandmarker.create_from_options(opts)
        self._ts = 0

    def gesto(self, frame_bgr):
        import mediapipe as mp

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        self._ts += 33
        res = self.landmarker.detect_for_video(mp_img, self._ts)
        if not res.hand_landmarks:
            return "none", None
        return clasificar_gesto(res.hand_landmarks[0]), res.hand_landmarks[0]


class Percepcion:
    def __init__(self, yolo_path, mano_path):
        self.yolo = YoloDetector(yolo_path)
        self.mano = Mano(mano_path)

    def procesar(self, frame_bgr):
        t0 = time.perf_counter()
        objetos = self.yolo.detectar(frame_bgr)
        t_yolo = (time.perf_counter() - t0) * 1000
        t1 = time.perf_counter()
        gesto, _lm = self.mano.gesto(frame_bgr)
        t_mano = (time.perf_counter() - t1) * 1000
        return {
            "gesto": gesto,
            "objetos": objetos,
            "yolo_ms": t_yolo,
            "mano_ms": t_mano,
        }
