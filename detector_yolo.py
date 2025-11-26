"""
Detector de Buracos com YOLO (ONNX)
===================================
Usa modelo YOLO11 treinado para detecção precisa de buracos.
"""

from typing import List, Tuple, Optional
import cv2
import numpy as np
import os


class YOLOPotholeDetector:
    """
    Detector de buracos usando modelo YOLO exportado para ONNX.
    
    O modelo ONNX pode ser executado com OpenCV DNN, que já está
    disponível no Android via python-for-android.
    """

    def __init__(
        self,
        model_path: str = "pothole_detector.onnx",
        conf_threshold: float = 0.5,
        nms_threshold: float = 0.4,
        input_size: Tuple[int, int] = (320, 320)
    ):
        """
        Args:
            model_path: Caminho para o modelo ONNX
            conf_threshold: Confiança mínima para detecção (0.5 = 50%)
            nms_threshold: Threshold para Non-Maximum Suppression
            input_size: Tamanho de entrada do modelo (largura, altura)
        """
        self.conf_threshold = conf_threshold
        self.nms_threshold = nms_threshold
        self.input_size = input_size
        self.net = None
        self.model_loaded = False
        
        # Tenta carregar o modelo
        self._load_model(model_path)

    def _load_model(self, model_path: str) -> bool:
        """Carrega o modelo ONNX."""
        # Lista de possíveis locais do modelo
        possible_paths = [
            model_path,
            os.path.join(os.path.dirname(__file__), model_path),
            os.path.join(os.path.dirname(__file__), "models", model_path),
            f"/data/data/org.detector.buracos.potholedetector/files/{model_path}",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                try:
                    self.net = cv2.dnn.readNetFromONNX(path)
                    # Usa OpenCL se disponível (GPU móvel)
                    self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                    self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                    self.model_loaded = True
                    print(f"Modelo YOLO carregado: {path}")
                    return True
                except Exception as e:
                    print(f"Erro ao carregar modelo {path}: {e}")
        
        print("⚠️ Modelo ONNX não encontrado. Usando fallback com heurísticas.")
        return False

    def detect(self, frame: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        """
        Detecta buracos no frame.

        Args:
            frame: Imagem BGR (formato OpenCV)

        Returns:
            Lista de tuplas (x, y, w, h, confidence) com coordenadas normalizadas (0-1)
        """
        if frame is None or frame.size == 0:
            return []

        if not self.model_loaded:
            # Fallback para detector baseado em heurísticas
            return self._detect_fallback(frame)

        try:
            height, width = frame.shape[:2]
            
            # Pré-processamento para YOLO
            blob = cv2.dnn.blobFromImage(
                frame,
                scalefactor=1/255.0,
                size=self.input_size,
                mean=(0, 0, 0),
                swapRB=True,
                crop=False
            )
            
            # Inferência
            self.net.setInput(blob)
            outputs = self.net.forward()
            
            # Processar saída do YOLO
            detections = self._process_outputs(outputs, width, height)
            
            return detections

        except Exception as e:
            print(f"Erro na detecção YOLO: {e}")
            return self._detect_fallback(frame)

    def _process_outputs(
        self,
        outputs: np.ndarray,
        img_width: int,
        img_height: int
    ) -> List[Tuple[float, float, float, float, float]]:
        """
        Processa saída do modelo YOLO.
        
        A saída do YOLO11 tem formato [1, 5, N] onde:
        - 5 = [x_center, y_center, width, height, confidence]
        - N = número de detecções
        """
        detections = []
        boxes = []
        confidences = []
        
        # Formato YOLO11 ONNX: [1, 5, N] -> transpor para [N, 5]
        if len(outputs.shape) == 3:
            outputs = outputs[0].T
        
        for detection in outputs:
            if len(detection) >= 5:
                # Para YOLO com classes, pegar max class score
                if len(detection) > 5:
                    class_scores = detection[4:]
                    confidence = np.max(class_scores)
                else:
                    confidence = detection[4]
                
                if confidence >= self.conf_threshold:
                    # Coordenadas do centro e dimensões
                    cx, cy, w, h = detection[:4]
                    
                    # Normalizar para 0-1
                    cx_norm = cx / self.input_size[0]
                    cy_norm = cy / self.input_size[1]
                    w_norm = w / self.input_size[0]
                    h_norm = h / self.input_size[1]
                    
                    # Converter de centro para canto superior esquerdo
                    x_norm = cx_norm - w_norm / 2
                    y_norm = cy_norm - h_norm / 2
                    
                    # Clamp para 0-1
                    x_norm = max(0, min(1, x_norm))
                    y_norm = max(0, min(1, y_norm))
                    w_norm = max(0, min(1 - x_norm, w_norm))
                    h_norm = max(0, min(1 - y_norm, h_norm))
                    
                    boxes.append([x_norm, y_norm, w_norm, h_norm])
                    confidences.append(float(confidence))
        
        # Non-Maximum Suppression
        if boxes:
            # Converter para formato OpenCV NMS (pixels)
            boxes_px = [[int(b[0]*100), int(b[1]*100), int(b[2]*100), int(b[3]*100)] for b in boxes]
            indices = cv2.dnn.NMSBoxes(boxes_px, confidences, self.conf_threshold, self.nms_threshold)
            
            if len(indices) > 0:
                for i in indices.flatten():
                    detections.append((
                        boxes[i][0],
                        boxes[i][1],
                        boxes[i][2],
                        boxes[i][3],
                        confidences[i]
                    ))
        
        # Ordenar por confiança e limitar
        detections.sort(key=lambda x: x[4], reverse=True)
        return detections[:5]

    def _detect_fallback(self, frame: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        """
        Fallback: detector baseado em heurísticas quando modelo ONNX não está disponível.
        MUITO menos preciso que YOLO - apenas para não quebrar o app.
        """
        # Importar detector de heurísticas
        try:
            from detector_heuristic import HeuristicPotholeDetector
            fallback = HeuristicPotholeDetector(min_confidence=0.85)
            return fallback.detect(frame)
        except:
            return []


# Alias para compatibilidade
PotholeDetector = YOLOPotholeDetector
