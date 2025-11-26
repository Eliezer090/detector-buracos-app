# 🚗 Detector de Buracos - App Android

Aplicativo Android que usa a câmera traseira do celular e processamento de imagem (IA) para detectar buracos na pista em tempo real enquanto você dirige.

## 📱 Funcionalidades

- ✅ **Detecção em tempo real** usando câmera traseira
- ✅ **Alertas visuais** com overlay vermelho
- ✅ **Vibração** quando detecta buraco
- ✅ **Contador** de buracos detectados
- ✅ **Modo paisagem** otimizado para painel do carro
- ✅ **Baixo consumo** de bateria (8 FPS)

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
| Framework | Python 3.10 + Kivy 2.3.0 |
| Processamento de Imagem | OpenCV |
| Build Android | Buildozer + python-for-android |
| CI/CD | GitHub Actions |

## 🚀 Build

### Automático (GitHub Actions)

1. Faça push para branch `main` ou `master`
2. O workflow `.github/workflows/build.yml` será executado
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

## 🎯 Como Funciona

1. **Captura**: A câmera traseira captura frames a 8 FPS
2. **ROI**: Analisa apenas a metade inferior da imagem (região da pista)
3. **Pré-processamento**: 
   - Conversão para escala de cinza
   - Equalização de histograma (CLAHE)
   - Gaussian blur
4. **Detecção**: 
   - Detecção de bordas (Canny)
   - Operações morfológicas
   - Análise de contornos
5. **Classificação**: Cada contorno é analisado por:
   - Circularidade (buracos são arredondados)
   - Proporção (não muito alongados)
   - Intensidade (buracos são escuros)
   - Contraste local
6. **Alerta**: Se confiança > 45%, vibra e mostra overlay

## 📝 Licença

MIT License
