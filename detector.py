"""
Detector de Buracos com OpenCV - Versão Otimizada
=================================================
Usa processamento de imagem avançado para detectar buracos na pista
com alta precisão e baixa latência.
"""

from typing import List, Tuple, Optional
import cv2
import numpy as np


class PotholeDetector:
    """
    Detector de buracos otimizado para tempo real.
    
    Usa uma combinação de técnicas:
    - Detecção de bordas adaptativa
    - Análise morfológica
    - Scoring multi-critério
    """

    __slots__ = [
        'min_confidence', 'min_area_ratio', 'max_area_ratio',
        'roi_y_start', '_kernel_small', '_kernel_large', '_clahe',
        '_frame_count', '_last_detections'
    ]

    def __init__(self, min_confidence: float = 0.40):
        """
        Args:
            min_confidence: Confiança mínima (0.0-1.0) para reportar detecção.
        """
        self.min_confidence = min_confidence
        
        # Parâmetros de detecção otimizados
        self.min_area_ratio = 0.001    # 0.1% do frame
        self.max_area_ratio = 0.15     # 15% do frame
        self.roi_y_start = 0.35        # Começa em 35% (mais área de pista)
        
        # Kernels pré-computados (evita recriar a cada frame)
        self._kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        self._kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        
        # CLAHE pré-configurado
        self._clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        
        # Tracking para estabilidade
        self._frame_count = 0
        self._last_detections: List = []

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

        self._frame_count += 1

        try:
            height, width = frame.shape[:2]
            
            # === 1. EXTRAÇÃO DE ROI ===
            roi_y = int(height * self.roi_y_start)
            roi = frame[roi_y:, :]
            roi_h, roi_w = roi.shape[:2]
            
            # === 2. PRÉ-PROCESSAMENTO OTIMIZADO ===
            # Redimensiona para processamento mais rápido se muito grande
            scale = 1.0
            if roi_w > 640:
                scale = 640.0 / roi_w
                roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            
            # Converte para escala de cinza
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            
            # Equalização adaptativa de histograma
            enhanced = self._clahe.apply(gray)
            
            # Blur bilateral (preserva bordas melhor que Gaussian)
            blurred = cv2.bilateralFilter(enhanced, 5, 50, 50)
            
            # === 3. DETECÇÃO DE BORDAS MULTI-ESCALA ===
            # Canny com thresholds adaptativos
            median_val = np.median(blurred)
            lower = int(max(0, 0.5 * median_val))
            upper = int(min(255, 1.5 * median_val))
            edges = cv2.Canny(blurred, lower, upper)
            
            # === 4. OPERAÇÕES MORFOLÓGICAS ===
            # Fecha gaps nas bordas
            closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, self._kernel_small, iterations=2)
            # Dilata para conectar regiões próximas
            dilated = cv2.dilate(closed, self._kernel_small, iterations=1)
            
            # === 5. ENCONTRA E ANALISA CONTORNOS ===
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Limites de área
            scaled_roi_h, scaled_roi_w = dilated.shape[:2]
            frame_area = scaled_roi_w * scaled_roi_h
            min_area = frame_area * self.min_area_ratio
            max_area = frame_area * self.max_area_ratio
            
            detections = []
            
            for contour in contours:
                area = cv2.contourArea(contour)
                
                # Filtra por área
                if area < min_area or area > max_area:
                    continue
                
                # Bounding box
                x, y, w, h = cv2.boundingRect(contour)
                
                # Filtra aspectos muito extremos
                aspect = max(w, h) / (min(w, h) + 1)
                if aspect > 5:
                    continue
                
                # Extrai patch para análise
                patch = gray[y:y+h, x:x+w] if y+h <= gray.shape[0] and x+w <= gray.shape[1] else None
                
                # Calcula confiança
                confidence = self._compute_confidence(contour, area, w, h, patch, blurred)
                
                if confidence >= self.min_confidence:
                    # Converte de volta para coordenadas originais
                    x_orig = x / scale
                    y_orig = y / scale
                    w_orig = w / scale
                    h_orig = h / scale
                    
                    # Normaliza para frame completo
                    x_norm = x_orig / roi_w
                    y_norm = (y_orig + (roi_y if scale == 1.0 else roi_y)) / height
                    w_norm = w_orig / roi_w
                    h_norm = h_orig / height
                    
                    detections.append((x_norm, y_norm, w_norm, h_norm, confidence))
            
            # Ordena por confiança
            detections.sort(key=lambda d: d[4], reverse=True)
            
            # Non-maximum suppression simples
            detections = self._nms(detections, iou_threshold=0.3)
            
            # Mantém top 5
            detections = detections[:5]
            
            # Atualiza cache
            self._last_detections = detections
            
            return detections

        except Exception as e:
            # Em produção, retorna última detecção válida em caso de erro
            return self._last_detections if self._last_detections else []

    def _compute_confidence(
        self,
        contour: np.ndarray,
        area: float,
        w: int,
        h: int,
        patch: Optional[np.ndarray],
        full_gray: np.ndarray
    ) -> float:
        """
        Calcula score de confiança multi-critério.
        
        Critérios:
        1. Circularidade (buracos tendem a ser arredondados)
        2. Proporção de aspecto (não muito alongado)
        3. Intensidade (buracos são escuros)
        4. Contraste local (borda definida)
        5. Convexidade (forma convexa)
        """
        score = 0.0
        
        # 1. CIRCULARIDADE (peso: 25%)
        perimeter = cv2.arcLength(contour, True)
        if perimeter > 0:
            circularity = 4 * np.pi * area / (perimeter ** 2)
            # Buracos geralmente têm circularidade 0.4-0.9
            if 0.3 <= circularity <= 1.0:
                score += 0.25 * min(circularity / 0.7, 1.0)
            else:
                score += 0.25 * 0.3  # Penalidade
        
        # 2. PROPORÇÃO (peso: 15%)
        aspect = max(w, h) / (min(w, h) + 1)
        if aspect <= 1.5:
            score += 0.15
        elif aspect <= 2.5:
            score += 0.15 * 0.7
        elif aspect <= 4.0:
            score += 0.15 * 0.4
        
        # 3. INTENSIDADE (peso: 30%) - buracos são escuros
        if patch is not None and patch.size > 0:
            mean_intensity = np.mean(patch)
            # Normaliza: 0=preto (bom), 255=branco (ruim)
            darkness = 1.0 - (mean_intensity / 255.0)
            # Buracos devem ser significativamente escuros
            if darkness > 0.5:
                score += 0.30 * darkness
            else:
                score += 0.30 * darkness * 0.5
        
        # 4. CONTRASTE LOCAL (peso: 20%)
        if patch is not None and patch.size > 0:
            std_dev = np.std(patch)
            # Buracos têm textura interna variada
            contrast = min(std_dev / 40.0, 1.0)
            score += 0.20 * contrast
        
        # 5. CONVEXIDADE (peso: 10%)
        try:
            hull = cv2.convexHull(contour)
            hull_area = cv2.contourArea(hull)
            if hull_area > 0:
                convexity = area / hull_area
                score += 0.10 * convexity
        except:
            pass
        
        return min(score, 1.0)

    def _nms(
        self,
        detections: List[Tuple[float, float, float, float, float]],
        iou_threshold: float = 0.3
    ) -> List[Tuple[float, float, float, float, float]]:
        """
        Non-Maximum Suppression para remover detecções sobrepostas.
        """
        if len(detections) <= 1:
            return detections
        
        # Ordena por confiança (já deve estar ordenado, mas garante)
        detections = sorted(detections, key=lambda x: x[4], reverse=True)
        
        keep = []
        while detections:
            best = detections.pop(0)
            keep.append(best)
            
            # Remove detecções muito sobrepostas com a melhor
            detections = [
                d for d in detections
                if self._iou(best, d) < iou_threshold
            ]
        
        return keep

    @staticmethod
    def _iou(box1: Tuple, box2: Tuple) -> float:
        """Calcula Intersection over Union entre duas caixas."""
        x1, y1, w1, h1 = box1[:4]
        x2, y2, w2, h2 = box2[:4]
        
        # Coordenadas da interseção
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        
        if xi2 <= xi1 or yi2 <= yi1:
            return 0.0
        
        inter_area = (xi2 - xi1) * (yi2 - yi1)
        box1_area = w1 * h1
        box2_area = w2 * h2
        union_area = box1_area + box2_area - inter_area
        
        return inter_area / union_area if union_area > 0 else 0.0
