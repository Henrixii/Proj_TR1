# Simulador TR1 — Camadas Física e de Enlace

Trabalho final de **Teleinformática e Redes 1 (UnB)**. O simulador é um chat de texto entre duas estações: cada mensagem desce pelas camadas do transmissor, atravessa um meio de comunicação com ruído e sobe pelas camadas do receptor. A tela mostra a saída de cada etapa, lado a lado para transmissor (TX) e receptor (RX), como na Figura 1 do enunciado.

## Como executar

Requer Python 3.10 ou mais novo.

Com [uv](https://docs.astral.sh/uv/):

```bash
uv run streamlit run Simulador.py
```

Ou com pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install streamlit matplotlib
streamlit run Simulador.py
```

A interface abre no navegador. Na primeira execução o Streamlit pode pedir um e-mail no terminal: basta apertar Enter.

## Como usar

1. Na barra lateral (**Configuração geral**), escolha o enquadramento, a detecção ou correção de erros, as modulações e o ruído do meio.
2. No **Chat**, escreva na Estação A ou na Estação B. Quem escreve é o transmissor; a outra estação é o receptor e mostra o texto como ele chegou, com o resultado da verificação de erros.
3. Em **Por dentro da transmissão**, escolha uma mensagem e um quadro para ver as 13 etapas do caminho: texto, bits, quadro, quadro com código de erro e os sinais em volts.

Para ver erros acontecendo, aumente o desvio padrão σ do ruído. O 32-QAM começa a errar perto de σ = 1 V; o NRZ-Polar só perto de σ = 3 V (com amplitude de 1 V).

## O que está implementado

| Enunciado | Técnicas | Onde |
|---|---|---|
| 1.1 Meio de comunicação | Sinal em volts, ruído gaussiano n(x, σ) ajustável | `Simulador.meio_de_comunicacao` |
| 1.2 Banda base | NRZ-Polar, Manchester, Bipolar | `CamadaFisica.py` |
| 1.2 Portadora | ASK, FSK, 8PSK, 32-QAM | `CamadaFisica.py` |
| 1.3 Enquadramento | Contagem de caracteres, entrelaçamento de bits, inserção de bytes, inserção de bits | `CamadaEnlace.py` |
| 1.3 Detecção | Bit de paridade par, checksum, CRC-32 (IEEE 802) | `CamadaEnlace.py` |
| 1.3 Correção | Hamming | `CamadaEnlace.py` |
| 1.4 Aplicação | Chat de texto, texto ↔ bits | `Simulador.py` e `InterfaceGUI.py` |

Nenhuma biblioteca externa implementa os protocolos: os cálculos usam só `math` e `random` da biblioteca padrão. Streamlit e matplotlib são usados apenas para a tela.

## Arquivos

```
CamadaFisica.py    codificação banda base e modulação por portadora (ida e volta)
CamadaEnlace.py    enquadramento, detecção e correção de erros (ida e volta)
InterfaceGUI.py    tela: configuração, chat e saída de cada camada
Simulador.py       rotina principal: threads TX e RX e o meio de comunicação
```

## Caminho de uma mensagem

```
Thread TX                                              Thread RX
 1 entrada de texto                                    13 saída de texto
 2 codificador em bits                                 12 desenquadramento
 3 enquadramento                                       11 detecção e correção de erros
 4 detecção e correção de erros                        10 bits recebidos
 5 codificador banda base                               9 decodificador banda base
 6 modulador  ──────►  7 meio (ruído)  ──────►          8 demodulador
```

As duas threads são criadas em `Simulador.enviar_mensagem` e se comunicam por uma fila, que faz o papel do fio entre as estações. Mensagens maiores que o tamanho máximo de quadro são divididas em vários quadros.

## Decisões onde o enunciado é omisso

- **Ordem na camada de enlace:** o transmissor enquadra e depois anexa o código de erro (seção 1.3 [2/3]: "adicione redundâncias aos quadros gerados na subetapa anterior"). O receptor faz o caminho inverso.
- **Banda base e portadora juntas:** em "Nenhuma (banda base)", o sinal do codificador escolhido vai direto para o meio. Com portadora, o codificador banda base gera NRZ-Polar, que alimenta o modulador, e o demodulador devolve NRZ ao decodificador (setas "NRZ" da Figura 1).
- **Tamanho do EDC:** só o checksum permite escolher (8, 16 ou 32 bits). Paridade tem 1 bit, CRC-32 tem 32 bits e o Hamming usa 3 bits de paridade a cada 4 bits de dados.
- **Contagem de caracteres:** o cabeçalho de 8 bits guarda a quantidade de bytes de dados, sem contar o próprio cabeçalho.
- **Entrelaçamento de bits:** os dados formam uma matriz com 1 byte por linha; o quadro leva o número de linhas, os dados e uma linha final com a paridade par de cada coluna.
- **Manchester:** bit 0 é alto→baixo e bit 1 é baixo→alto (convenção IEEE 802.3).
- **ASK e FSK:** no ASK o bit 0 é ausência de portadora; no FSK o bit 1 usa o dobro da frequência do bit 0.
- **8PSK e 32-QAM:** o último símbolo é completado com zeros, e o receptor é avisado de quantos bits o quadro tem para descartá-los.
- **Hamming:** Hamming(7,4), corrige 1 bit por bloco de 7 bits.
- **Quadros com erro:** são sinalizados (não descartados); o texto é mostrado como chegou.
- **Caracteres:** cada caractere vira 8 bits. Os que não cabem em 8 bits (emojis, por exemplo) são trocados por `?`.
