"""
Detector de Buracos com OpenCV
==============================
Usa processamento de imagem para detectar potenciais buracos na pista.
"""

from typing import List, Tuple
import cv2
import numpy as np


class PotholeDetector:
    """Detector de buracos baseado em análise de imagem."""

    def __init__(self, min_confidence: float = 0.45):
        """
        Args:
            min_confidence: Confiança mínima para considerar uma detecção válida.
        """
        self.min_confidence = min_confidence
        
        # Parâmetros de detecção
        self.min_area_ratio = 0.002   # Área mínima relativa ao frame
        self.max_area_ratio = 0.25    # Área máxima relativa ao frame
        
        # ROI: região de interesse (metade inferior da imagem = pista)
        self.roi_y_start = 0.4        # Começa em 40% da altura

    def detect(self, frame: np.ndarray) -> List[Tuple[float, float, float, float, float]]:
        """
        Detecta buracos no frame.

        Args:
            frame: Imagem BGR do OpenCV

        Returns:
            Lista de detecções: [(x_norm, y_norm, w_norm, h_norm, confidence), ...]
            Coordenadas normalizadas (0-1)
        """
        if frame is None or frame.size == 0:
            return []

        try:
            height, width = frame.shape[:2]
            
            # Extrai ROI (região inferior = pista)
            roi_y = int(height * self.roi_y_start)
            roi = frame[roi_y:, :]
            roi_height = height - roi_y
            
            # Pré-processamento
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Equalização de histograma para melhorar contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            
            # Blur para reduzir ruído
            blurred = cv2.GaussianBlur(enhanced, (5, 5), 0)
            
            # Detecção de bordas
            edges = cv2.Canny(blurred, 50, 150)
            
            # Operações morfológicas
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)
            dilated = cv2.dilate(closed, kernel, iterations=1)
            
            # Encontra contornos
            contours, _ = cv2.findContours(
                dilated, 
                cv2.RETR_EXTERNAL, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            detections = []
            frame_area = width * roi_height
            min_area = frame_area * self.min_area_ratio
            max_area = frame_area * self.max_area_ratio
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                if area < min_area or area > max_area:
                    continue
                
                # Bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Análise de forma
                confidence = self._analyze_contour(contour, area, w, h, gray[y:y+h, x:x+w])
                
                if confidence >= self.min_confidence:
                    # Converte para coordenadas normalizadas do frame completo
                    x_norm = x / width
                    y_norm = (y + roi_y) / height
                    w_norm = w / width
                    h_norm = h / height
                    
                    detections.append((x_norm, y_norm, w_norm, h_norm, confidence))
            
            # Ordena por confiança e retorna top 5
            detections.sort(key=lambda d: d[4], reverse=True)
            return detections[:5]

        except Exception as e:
            print(f"Erro na detecção: {e}")
            return []

    def _analyze_contour(
        self, 
        contour: np.ndarray, 
        area: float, 
        width: int, 
        height: int,
        roi_patch: np.ndarray
    ) -> float:
        """
        Analisa um contorno e retorna uma pontuação de confiança.
        
        Buracos tendem a ser:
        - Escuros (baixa intensidade)
        - Arredondados ou elípticos
        - Com borda bem definida
        """
        scores = []
        
        # 1. Circularidade (buracos são geralmente arredondados)
        perimeter = cv2.arcLength(contour, True)
        if perimeter > 0:
            circularity = 4 * np.pi * area / (perimeter ** 2)
            # Score: 1.0 para círculo perfeito, diminui para formas alongadas
            circ_score = min(circularity, 1.0)
            scores.append(circ_score * 0.25)
        
        # 2. Aspecto (não muito alongado)
        aspect_ratio = max(width, height) / (min(width, height) + 1)
        # Penaliza formas muito alongadas (não parecem buracos)
        if aspect_ratio > 4:
            aspect_score = 0.2
        elif aspect_ratio > 2:
            aspect_score = 0.5
        else:
            aspect_score = 1.0
        scores.append(aspect_score * 0.2)
        
        # 3. Intensidade (buracos são escuros)
        if roi_patch.size > 0:
            mean_intensity = np.mean(roi_patch)
            # Quanto mais escuro, maior o score
            intensity_score = 1.0 - (mean_intensity / 255.0)
            scores.append(intensity_score * 0.35)
        
        # 4. Contraste com vizinhança
        if roi_patch.size > 0:
            std_intensity = np.std(roi_patch)
            # Buracos têm variação interna moderada
            contrast_score = min(std_intensity / 50.0, 1.0)
            scores.append(contrast_score * 0.2)
        
        return sum(scores)
