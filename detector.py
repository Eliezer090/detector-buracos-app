"""
Módulo de detecção de buracos usando AI
Utiliza YOLOv5 ou detecção baseada em características visuais
"""

import cv2
import numpy as np
from typing import List, Tuple
import os


class PotholeDetector:
    """Detector de buracos na pista usando visão computacional e AI"""
    
    def __init__(self, use_yolo=False, model_path=None):
        """
        Inicializa o detector
        
        Args:
            use_yolo: Se True, tenta usar modelo YOLO treinado
            model_path: Caminho para modelo customizado
        """
        self.use_yolo = use_yolo
        self.model = None
        self.confidence_threshold = 0.5
        
        if use_yolo and model_path and os.path.exists(model_path):
            self.load_yolo_model(model_path)
        else:
            # Fallback para detecção baseada em características
            print("Usando detecção baseada em características visuais")
    
    def load_yolo_model(self, model_path):
        """Carrega modelo YOLO treinado"""
        try:
            import torch
            # Carrega modelo YOLOv5 customizado ou pré-treinado
            self.model = torch.hub.load('ultralytics/yolov5', 'custom', 
                                        path=model_path, force_reload=False)
            self.model.conf = self.confidence_threshold
            print(f"Modelo YOLO carregado: {model_path}")
        except Exception as e:
            print(f"Erro ao carregar modelo YOLO: {e}")
            self.use_yolo = False
    
    def detect(self, frame: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        """
        Detecta buracos no frame
        
        Args:
            frame: Imagem em formato numpy array (BGR)
            
        Returns:
            Lista de detecções: [(x, y, w, h, confidence), ...]
            onde x, y, w, h são normalizados entre 0 e 1
        """
        if self.use_yolo and self.model is not None:
            return self.detect_with_yolo(frame)
        else:
            return self.detect_with_features(frame)
    
    def detect_with_yolo(self, frame: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        """Detecta buracos usando modelo YOLO"""
        try:
            # Inferência
            results = self.model(frame)
            detections = []
            
            # Processa resultados
            for *box, conf, cls in results.xyxy[0]:
                x1, y1, x2, y2 = box
                h, w = frame.shape[:2]
                
                # Normaliza coordenadas
                x_norm = float(x1) / w
                y_norm = float(y1) / h
                w_norm = float(x2 - x1) / w
                h_norm = float(y2 - y1) / h
                
                detections.append((x_norm, y_norm, w_norm, h_norm, float(conf)))
            
            return detections
        except Exception as e:
            print(f"Erro na detecção YOLO: {e}")
            return []
    
    def detect_with_features(self, frame: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        """
        Detecta buracos usando características visuais
        Buracos geralmente aparecem como regiões escuras, irregulares e com bordas definidas
        """
        detections = []
        
        try:
            h, w = frame.shape[:2]
            
            # Pré-processamento
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (7, 7), 0)
            
            # Detecção de bordas
            edges = cv2.Canny(blurred, 50, 150)
            
            # Operações morfológicas para conectar bordas
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
            dilated = cv2.dilate(closed, kernel, iterations=2)
            
            # Encontra contornos
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Filtra por área mínima (ajustar conforme necessário)
                if area < 500 or area > 50000:
                    continue
                
                # Calcula retângulo delimitador
                x, y, w_box, h_box = cv2.boundingRect(contour)
                
                # Calcula razão de aspecto
                aspect_ratio = float(w_box) / h_box if h_box > 0 else 0
                
                # Filtra por razão de aspecto (buracos tendem a ser circulares/ovais)
                if aspect_ratio < 0.3 or aspect_ratio > 3.0:
                    continue
                
                # Calcula circularidade
                perimeter = cv2.arcLength(contour, True)
                if perimeter == 0:
                    continue
                circularity = 4 * np.pi * area / (perimeter * perimeter)
                
                # Verifica intensidade (buracos são geralmente escuros)
                roi = gray[y:y+h_box, x:x+w_box]
                if roi.size == 0:
                    continue
                mean_intensity = np.mean(roi)
                
                # Calcula confiança baseada em múltiplos fatores
                confidence = 0.0
                
                # Buracos são geralmente escuros
                if mean_intensity < 100:
                    confidence += 0.3
                
                # Boa circularidade indica possível buraco
                if circularity > 0.4:
                    confidence += 0.4
                
                # Razão de aspecto próxima de 1 (circular)
                if 0.7 <= aspect_ratio <= 1.3:
                    confidence += 0.3
                
                # Apenas adiciona se confiança é suficiente
                if confidence >= self.confidence_threshold:
                    # Normaliza coordenadas
                    x_norm = x / w
                    y_norm = y / h
                    w_norm = w_box / w
                    h_norm = h_box / h
                    
                    detections.append((x_norm, y_norm, w_norm, h_norm, confidence))
            
        except Exception as e:
            print(f"Erro na detecção por características: {e}")
        
        return detections
    
    def set_confidence_threshold(self, threshold: float):
        """Define threshold de confiança para detecções"""
        self.confidence_threshold = max(0.0, min(1.0, threshold))
        if self.model:
            self.model.conf = self.confidence_threshold
