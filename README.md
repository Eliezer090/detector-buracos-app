# 🚗 Detector de Buracos - App Android

Aplicativo Android que usa a câmera traseira do celular e processamento de imagem (OpenCV) para detectar buracos na pista em tempo real enquanto você dirige.

## 📱 Funcionalidades

- ✅ **Detecção em tempo real** usando câmera traseira
- ✅ **Alertas visuais** com overlay vermelho
- ✅ **Vibração** quando detecta buraco
- ✅ **Contador** de buracos detectados
- ✅ **Modo paisagem** otimizado para painel do carro
- ✅ **10 FPS** de processamento (bom equilíbrio performance/bateria)
- ✅ **NMS** (Non-Maximum Suppression) para evitar detecções duplicadas

## 🏗️ Estrutura do Projeto

```
AppViewBurracos/
├── main.py           # App principal (Kivy)
├── detector.py       # Algoritmo de detecção (OpenCV)
├── buildozer.spec    # Configuração de build Android
├── requirements.txt  # Dependências Python
└── .github/
    └── workflows/
        └── build.yml # GitHub Actions CI/CD
```

## 🔧 Tecnologias

| Componente | Tecnologia |
|------------|------------|
| Framework | Python 3.10 + Kivy 2.2.0 |
| Processamento de Imagem | OpenCV + NumPy |
| Build Android | Buildozer + python-for-android |
| CI/CD | GitHub Actions (ubuntu-22.04) |

## 🚀 Build

### Automático (GitHub Actions)

1. Faça push para branch `main` ou `master`
2. O workflow `.github/workflows/build.yml` será executado (~40-60 min)
3. Baixe o APK na aba "Actions" → "Artifacts"

### Manual (Local)

```bash
# Instalar dependências
pip install buildozer cython==0.29.36

# Build debug
buildozer android debug

# O APK estará em bin/
```

## 📋 Requisitos

- **Android**: API 24+ (Android 7.0+)
- **Permissões**: Câmera, Vibração

## 🎯 Como Funciona o Detector

### Pipeline de Processamento

1. **Captura**: Câmera traseira a 10 FPS
2. **ROI**: Região de interesse (65% inferior = pista)
3. **Redimensionamento**: Max 640px largura para performance
4. **Pré-processamento**: 
   - Escala de cinza
   - CLAHE (equalização adaptativa)
   - Filtro bilateral (preserva bordas)
5. **Detecção de Bordas**: Canny com thresholds adaptativos
6. **Morfologia**: Close + Dilate para conectar regiões

### Scoring Multi-Critério (Confiança)

| Critério | Peso | Descrição |
|----------|------|-----------|
| Circularidade | 25% | Buracos são arredondados |
| Proporção | 15% | Não muito alongados |
| Intensidade | 30% | Buracos são escuros |
| Contraste | 20% | Borda bem definida |
| Convexidade | 10% | Forma convexa |

7. **NMS**: Remove detecções sobrepostas (IoU > 0.3)
8. **Alerta**: Se confiança ≥ 40%, vibra e mostra overlay

## 📝 Licença

MIT License
