"""
Detector de Buracos - Módulo Principal
======================================
Usa YOLO treinado para detecção precisa. 
Fallback para heurísticas se modelo não disponível.
"""

from typing import List, Tuple
import os


class PotholeDetector:
    """
    Detector de buracos inteligente.
    
    Prioridade:
    1. Modelo YOLO ONNX (se disponível) - ALTA PRECISÃO
    2. Heurísticas OpenCV (fallback) - BAIXA PRECISÃO
    """

    def __init__(self, min_confidence: float = 0.50):
        """
        Args:
            min_confidence: Confiança mínima (0.0-1.0) para reportar detecção.
        """
        self.min_confidence = min_confidence
        self._detector = None
        self._init_detector()

    def _init_detector(self):
        """Inicializa o melhor detector disponível."""
        # Tenta carregar detector YOLO primeiro
        try:
            from detector_yolo import YOLOPotholeDetector
            self._detector = YOLOPotholeDetector(
                conf_threshold=0.1  # Baixo para capturar tudo, filtrar na UI
            )
            if self._detector.model_loaded:
                print("✅ Usando detector YOLO (alta precisão)")
                return
        except Exception as e:
            print(f"YOLO não disponível: {e}")

        # Fallback para heurísticas
        try:
            from detector_heuristic import HeuristicPotholeDetector
            self._detector = HeuristicPotholeDetector(
                min_confidence=0.2  # Baixo para capturar tudo, filtrar na UI
            )
            print("⚠️ Usando detector heurístico (fallback)")
        except Exception as e:
            print(f"Erro ao inicializar detector: {e}")
            self._detector = None

    def detect(self, frame, return_all: bool = True) -> List[Tuple[float, float, float, float, float]]:
        """
        Detecta buracos no frame.

        Args:
            frame: Imagem BGR (formato OpenCV)
            return_all: Se True, retorna todas as detecções. Se False, filtra por min_confidence.

        Returns:
            Lista de tuplas (x, y, w, h, confidence) com coordenadas normalizadas (0-1)
        """
        if self._detector is None:
            return []
        
        try:
            detections = self._detector.detect(frame)
            if return_all:
                return detections
            # Filtra por confiança mínima
            return [d for d in detections if d[4] >= self.min_confidence]
        except Exception as e:
            print(f"Erro na detecção: {e}")
            return []

    @property
    def active_detector(self):
        """Retorna o detector ativo."""
        return self._detector

    @property
    def detector_name(self) -> str:
        """Retorna o nome do detector ativo."""
        if self._detector is None:
            return "Nenhum"
        return type(self._detector).__name__

    @property
    def is_yolo_available(self) -> bool:
        """Verifica se está usando YOLO."""
        try:
            from detector_yolo import YOLOPotholeDetector
            return isinstance(self._detector, YOLOPotholeDetector) and self._detector.model_loaded
        except:
            return False
