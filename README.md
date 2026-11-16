# PROJ_TR1 — Simulador de Camadas Física e de Enlace

Simuladores didáticos de um sistema de comunicação digital, para a disciplina **Teleinformática e Redes 1 (TR1) — UnB**. O repositório tem duas aplicações. As duas cobrem modulação, enquadramento e detecção ou correção de erros.

Requer Python 3.10 ou mais novo.

```bash
uv run streamlit run Simulador.py
```

Ou, com pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install streamlit matplotlib
```

## Chat local (`Simulador.py`)

Chat de texto entre duas estações na mesma tela. Cada mensagem desce pelas camadas do transmissor, atravessa um meio com ruído gaussiano e sobe pelas camadas do receptor. A interface mostra a saída de cada etapa, lado a lado.

```bash
uv run streamlit run Simulador.py
```

Na primeira execução o Streamlit pode pedir um e-mail no terminal: basta apertar Enter.

1. Na barra lateral, escolha o enquadramento, a detecção ou correção de erros, as modulações e o ruído do meio.
2. No chat, escreva na Estação A ou na Estação B. Quem escreve é o transmissor; a outra estação mostra o texto como chegou.
3. Em **Por dentro da transmissão**, escolha uma mensagem e um quadro para ver as etapas do caminho.

Para ver erros acontecendo, aumente o desvio padrão σ do ruído. O 32-QAM começa a errar perto de σ = 1 V; o NRZ-Polar só perto de σ = 3 V (com amplitude de 1 V).

| Enunciado | Técnicas | Onde |
|---|---|---|
| Meio de comunicação | Sinal em volts, ruído gaussiano n(x, σ) | `Simulador.py` |
| Banda base | NRZ-Polar, Manchester, Bipolar | `CamadaFisica.py` |
| Portadora | ASK, FSK, 8PSK, 32-QAM | `CamadaFisica.py` |
| Enquadramento | Contagem de caracteres, entrelaçamento de bits, inserção de bytes, inserção de bits | `CamadaEnlace.py` |
| Detecção | Bit de paridade par, checksum, CRC-32 (IEEE 802) | `CamadaEnlace.py` |
| Correção | Hamming (7,4) | `CamadaEnlace.py` |
| Aplicação | Chat de texto | `Simulador.py`, `InterfaceGUI.py` |

Os protocolos usam só `math` e `random` da biblioteca padrão. Streamlit e matplotlib desenham a tela.

```
CamadaFisica.py    banda base e portadora, ida e volta
CamadaEnlace.py    enquadramento, detecção e correção, ida e volta
InterfaceGUI.py    configuração, chat e saída de cada camada
Simulador.py       threads TX e RX e o meio de comunicação
```

O transmissor enquadra e depois anexa o código de erro. O receptor faz o caminho inverso. Em "Nenhuma (banda base)", o sinal do codificador vai direto ao meio. Com portadora, o codificador gera NRZ-Polar, que alimenta o modulador.

## Transmissor e receptor por socket (`interface.py` e `servidor.py`)

A interface envia o sinal por TCP e o servidor desfaz o processo: demodula, verifica erros e desenquadra a mensagem.

Em um terminal:

```bash
python servidor.py
```

Em outro:

```bash
streamlit run interface.py
```

| Peça | Arquivo |
|---|---|
| Interface Streamlit (transmissor) | `interface.py` |
| Servidor TCP (receptor) | `servidor.py` |
| Modulações, demodulações e ruído | `physical_layer.py` |
| Enquadramento | `link_layer.py` |
| Paridade, checksum, CRC-32 e Hamming | `deteccao_erros.py` |

Modulações banda base: NRZ-Polar, Manchester e Bipolar. Portadora: ASK, FSK, PSK e 16-QAM. Enquadramento: contagem de caracteres, inserção de bits e inserção de bytes.
