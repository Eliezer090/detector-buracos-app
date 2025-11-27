"""
Detector de Buracos com OpenCV - Fallback (Heurísticas)
=======================================================
Usado quando o modelo YOLO não está disponível.
ATENÇÃO: Menos preciso que YOLO - muitos falsos positivos possíveis.
"""

from typing import List, Tuple, Optional
import cv2
import numpy as np


class HeuristicPotholeDetector:
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

    def __init__(self, min_confidence: float = 0.20):
        """
        Args:
            min_confidence: Confiança mínima (0.0-1.0) para reportar detecção.
                           Default: 0.20 (20%) - captura mais detecções, filtro na UI.
        """
        self.min_confidence = min_confidence
        
        # Parâmetros de detecção - menos rigorosos para capturar mais
        self.min_area_ratio = 0.003    # 0.3% do frame
        self.max_area_ratio = 0.15     # 15% do frame
        self.roi_y_start = 0.40        # Começa em 40% (mais área de detecção)
        
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
        Calcula score de confiança multi-critério RIGOROSO.
        
        Para atingir 90%+ de confiança, o objeto deve:
        1. Ser significativamente escuro (buraco = sombra/asfalto danificado)
        2. Ter formato arredondado/oval (não alongado)
        3. Ter contraste claro com a vizinhança
        4. Estar na região esperada (pista)
        """
        # Se não temos patch, não podemos analisar bem
        if patch is None or patch.size < 100:
            return 0.0
        
        scores = []
        
        # 1. ESCURIDÃO CRÍTICA (peso: 35%) - buracos SÃO escuros
        mean_intensity = np.mean(patch)
        if mean_intensity > 120:
            # Muito claro para ser buraco - falha imediata
            return 0.0
        darkness_score = 1.0 - (mean_intensity / 120.0)
        scores.append(('darkness', darkness_score * 0.35))
        
        # 2. CONTRASTE COM VIZINHANÇA (peso: 25%)
        # Buraco deve ser mais escuro que ao redor
        try:
            # Pega região ao redor do contorno
            x, y, bw, bh = cv2.boundingRect(contour)
            margin = max(bw, bh) // 2
            y1 = max(0, y - margin)
            y2 = min(full_gray.shape[0], y + bh + margin)
            x1 = max(0, x - margin)
            x2 = min(full_gray.shape[1], x + bw + margin)
            
            neighborhood = full_gray[y1:y2, x1:x2]
            if neighborhood.size > 0:
                neighbor_mean = np.mean(neighborhood)
                # Buraco deve ser pelo menos 20% mais escuro que vizinhança
                contrast_ratio = (neighbor_mean - mean_intensity) / (neighbor_mean + 1)
                if contrast_ratio < 0.15:
                    return 0.0  # Sem contraste suficiente
                contrast_score = min(contrast_ratio / 0.4, 1.0)
                scores.append(('contrast', contrast_score * 0.25))
            else:
                scores.append(('contrast', 0.0))
        except:
            scores.append(('contrast', 0.0))
        
        # 3. CIRCULARIDADE (peso: 20%) - buracos são arredondados
        perimeter = cv2.arcLength(contour, True)
        if perimeter > 0:
            circularity = 4 * np.pi * area / (perimeter ** 2)
            if circularity < 0.2:
                return 0.0  # Muito irregular
            circ_score = min(circularity / 0.6, 1.0)
            scores.append(('circularity', circ_score * 0.20))
        else:
            return 0.0
        
        # 4. PROPORÇÃO (peso: 10%) - não muito alongado
        aspect = max(w, h) / (min(w, h) + 1)
        if aspect > 3.0:
            return 0.0  # Muito alongado (provavelmente faixa/rachadura)
        aspect_score = 1.0 - (aspect - 1.0) / 2.0
        scores.append(('aspect', max(0, aspect_score) * 0.10))
        
        # 5. TEXTURA INTERNA (peso: 10%) - buracos têm textura irregular
        std_dev = np.std(patch)
        if std_dev < 5:
            return 0.0  # Muito uniforme (provavelmente sombra)
        texture_score = min(std_dev / 30.0, 1.0)
        scores.append(('texture', texture_score * 0.10))
        
        # Soma final
        total = sum(s[1] for s in scores)
        
        return min(total, 1.0)

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
