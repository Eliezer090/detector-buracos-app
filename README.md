# 🚗 Detector de Buracos - Aplicativo Mobile

Aplicativo mobile que usa a câmera traseira do celular e Inteligência Artificial para detectar buracos na pista em tempo real, emitindo alertas visuais e sonoros.

## 📱 Características

- ✅ Detecção em tempo real usando câmera traseira
- ✅ Processamento com Inteligência Artificial
- ✅ Alertas visuais (overlay vermelho e caixas ao redor dos buracos)
- ✅ Alertas sonoros
- ✅ Contador de buracos detectados
- ✅ Interface otimizada para uso em modo landscape (painel do carro)
- ✅ Sistema de cooldown para evitar alertas excessivos

## 🎯 Como Funciona

1. O celular é posicionado no painel do carro com a câmera traseira voltada para a rua
2. O app processa os frames da câmera em tempo real (10 FPS)
3. A IA analisa cada frame buscando características de buracos:
   - Regiões escuras
   - Bordas definidas
   - Formato circular/oval
   - Tamanho compatível com buracos
4. Quando detecta um buraco, emite alerta visual e sonoro

## 🔧 Instalação

### Desktop (Desenvolvimento e Testes)

```bash
# Clone ou navegue até o diretório
cd c:\Users\es19237\Desktop\AreaTrabalho\Python\AppViewBurracos

# Crie um ambiente virtual
python -m venv venv
venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Execute o aplicativo
python main.py
```

### Android (Build do APK)

```bash
# Instale buildozer (necessário ter WSL ou Linux)
pip install buildozer

# No Linux/WSL:
buildozer android debug

# O APK será gerado em bin/potholedetector-1.0.0-debug.apk
# Transfira para o celular e instale
```

## 🧠 Modelos de IA

### Detecção por Características (Padrão)
O app vem configurado com um detector baseado em características visuais usando OpenCV:
- **Vantagens**: Funciona sem internet, leve, rápido
- **Desvantagens**: Menos preciso que deep learning

### Detecção com YOLO (Avançado)
Para maior precisão, você pode treinar ou usar um modelo YOLOv5:

1. **Obter modelo treinado**:
   - Treine seu próprio modelo com dataset de buracos
   - Ou use um modelo pré-treinado disponível online

2. **Configurar no código**:
```python
# No arquivo main.py, modifique:
self.detector = PotholeDetector(use_yolo=True, model_path='path/to/model.pt')
```

3. **Datasets sugeridos**:
   - [Pothole Dataset](https://www.kaggle.com/datasets/atulyakumar98/pothole-detection-dataset)
   - [Road Damage Dataset](https://github.com/sekilab/RoadDamageDetector)

## 📁 Estrutura do Projeto

```
AppViewBurracos/
├── main.py              # Interface principal do app (Kivy)
├── detector.py          # Módulo de detecção de buracos (AI)
├── requirements.txt     # Dependências Python
├── buildozer.spec       # Configuração para build Android
├── README.md           # Este arquivo
└── alert.wav           # Som de alerta (adicionar manualmente)
```

## ⚙️ Configurações

### Ajustar Sensibilidade
No arquivo `detector.py`, linha 23:
```python
self.confidence_threshold = 0.5  # Reduzir para mais detecções, aumentar para menos
```

### Ajustar Taxa de Processamento
No arquivo `main.py`, linha 93:
```python
Clock.schedule_interval(self.process_frame, 1.0 / 10.0)  # Alterar FPS aqui
```

### Ajustar Cooldown de Alertas
No arquivo `main.py`, linha 87:
```python
self.alert_cooldown = 2.0  # Segundos entre alertas
```

## 🔊 Adicionar Som de Alerta

1. Coloque um arquivo de áudio `alert.wav` ou `alert.mp3` no diretório do app
2. O som será reproduzido automaticamente quando um buraco for detectado

## 📱 Permissões Android

O app requer as seguintes permissões:
- `CAMERA` - Acesso à câmera traseira
- `WRITE_EXTERNAL_STORAGE` - Salvar logs (opcional)
- `READ_EXTERNAL_STORAGE` - Ler modelo de IA (opcional)
- `VIBRATE` - Vibração no alerta (futuro)
- `WAKE_LOCK` - Manter tela ligada durante uso

## 🚀 Melhorias Futuras

- [ ] Salvar localização GPS dos buracos detectados
- [ ] Upload de dados para servidor (mapa colaborativo)
- [ ] Modo noturno com ajuste de sensibilidade
- [ ] Calibração automática baseada na velocidade do carro
- [ ] Feedback háptico (vibração)
- [ ] Histórico de detecções
- [ ] Integração com Waze/Google Maps

## 🐛 Problemas Conhecidos

- Em ambientes com pouca luz, a detecção pode ser menos precisa
- Sombras e manchas de óleo podem ser confundidas com buracos
- Requer celular com boa câmera e processador razoável

## 📄 Licença

Este projeto é de código aberto para uso pessoal e educacional.

## 👨‍💻 Desenvolvimento

Para contribuir ou reportar bugs, entre em contato ou abra uma issue.

---

**⚠️ Atenção**: Este app é uma ferramenta auxiliar. Sempre dirija com atenção e não dependa exclusivamente do aplicativo para evitar buracos.
