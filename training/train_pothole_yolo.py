# 🚗 Treinamento YOLO para Detecção de Buracos
# =============================================
# Execute este notebook no Google Colab com GPU

# ============================================
# 1. INSTALAR DEPENDÊNCIAS
# ============================================

# !pip install ultralytics roboflow

# ============================================
# 2. BAIXAR DATASET DO ROBOFLOW
# ============================================

from roboflow import Roboflow

# Dataset recomendado: 11.763 imagens de buracos
# Acesse: https://universe.roboflow.com/project-saocp/pothole-fy5oo
# Crie uma conta gratuita e obtenha sua API key

rf = Roboflow(api_key="SUA_API_KEY_AQUI")  # Substitua pela sua API key
project = rf.workspace("project-saocp").project("pothole-fy5oo")
dataset = project.version(1).download("yolov8")

# ============================================
# 3. TREINAR MODELO YOLO11
# ============================================

from ultralytics import YOLO

# Usar YOLO11 nano para dispositivos móveis (mais leve e rápido)
model = YOLO("yolo11n.pt")  # ou yolo11s.pt para mais precisão

# Treinar
results = model.train(
    data=f"{dataset.location}/data.yaml",
    epochs=100,           # Mais épocas = melhor precisão
    imgsz=640,            # Tamanho da imagem
    batch=16,             # Ajuste conforme memória GPU
    device=0,             # GPU
    patience=20,          # Early stopping
    save=True,
    project="pothole_detection",
    name="yolo11n_pothole",
    
    # Augmentações para melhor generalização
    augment=True,
    hsv_h=0.015,
    hsv_s=0.7,
    hsv_v=0.4,
    degrees=10,
    translate=0.1,
    scale=0.5,
    fliplr=0.5,
    mosaic=1.0,
)

# ============================================
# 4. VALIDAR MODELO
# ============================================

metrics = model.val()
print(f"\n📊 Resultados da Validação:")
print(f"   mAP50: {metrics.box.map50:.3f}")
print(f"   mAP50-95: {metrics.box.map:.3f}")
print(f"   Precisão: {metrics.box.p[0]:.3f}")
print(f"   Recall: {metrics.box.r[0]:.3f}")

# ============================================
# 5. EXPORTAR PARA ONNX (Android)
# ============================================

# Exportar para ONNX (compatível com OpenCV no Android)
model.export(
    format="onnx",
    imgsz=320,          # Menor para dispositivo móvel
    simplify=True,      # Simplificar grafo
    opset=12,           # Versão ONNX compatível
    dynamic=False,      # Tamanho fixo para melhor performance
)

print("\n✅ Modelo exportado para ONNX!")
print("   Arquivo: pothole_detection/yolo11n_pothole/weights/best.onnx")
print("\n📱 Próximo passo: Copie o arquivo .onnx para o projeto Android")

# ============================================
# 6. TESTE RÁPIDO
# ============================================

# Testar em uma imagem
test_results = model.predict(
    source="path/to/test/image.jpg",
    conf=0.5,           # Confiança mínima
    save=True,
)

for r in test_results:
    print(f"Detecções: {len(r.boxes)}")
    for box in r.boxes:
        print(f"  - Confiança: {box.conf[0]:.2%}")
