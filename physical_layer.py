import numpy as np
import matplotlib.pyplot as plt
import re


# Tabela do 32-QAM: tabuleiro 6x6 de pontos (I, Q) sem os 4 cantos = 32 pontos.
# Os cantos saem porque ficam longe do centro e gastariam mais energia (mais volts).
# Cada ponto recebe um grupo de 5 bits: '00000', '00001', ..., '11111'.
# Os pontos são divididos pela distância do ponto mais afastado (5, 3), para que
# o pico do sinal seja exatamente a amplitude A escolhida (em volts).
def _montar_tabela_32qam():
    niveis = [-5, -3, -1, 1, 3, 5]
    maior_distancia = np.sqrt(5**2 + 3**2)
    pontos = []
    for Q in niveis:
        for I in niveis:
            eh_canto = abs(I) == 5 and abs(Q) == 5
            if not eh_canto:
                pontos.append((I / maior_distancia, Q / maior_distancia))
    return {f'{indice:05b}': ponto for indice, ponto in enumerate(pontos)}

PONTOS_32QAM = _montar_tabela_32qam()


class PhysicalLayer:
    def __init__(self):
        self.texto = ""
        self.bits = ""
        self.sinal = []
        self.tempo = []

    # Converte texto em uma sequência de bits (cada caractere vira 8 bits)
    def texto_para_bits(self, texto):
        self.texto = texto
        self.bits = ''.join(f'{ord(c):08b}' for c in texto)
        return self.bits

    # Converte uma string de bits (múltiplos de 8) de volta para texto
    def bits_para_texto(self, bits: str) -> str:
        if len(bits) % 8 != 0:
            raise ValueError("O número de bits deve ser múltiplo de 8.")
        texto = ''
        for i in range(0, len(bits), 8):
            byte = bits[i:i+8]
            caractere = chr(int(byte, 2))
            texto += caractere
        return texto

    # Modulação NRZ polar: bit 1 vira +A e bit 0 vira -A
    def nrz_polar(self, bits, A=1):
        self.sinal = [A if b == '1' else -A for b in bits]
        return self.sinal

    # Demodulação NRZ: decide pelo sinal (>=0 vira 1) -> aguenta ruido
    def demodular_nrz(self, sinal_str):
        amostras = [float(x) for x in sinal_str.split(',')]
        bits = ''.join(['1' if x >= 0 else '0' for x in amostras])
        return bits

    # Modulação Manchester: 0 → [A, -A], 1 → [-A, A]
    def manchester(self, bits, A=1):
        self.sinal = [v for b in bits for v in ([A, -A] if b == '0' else [-A, A])]
        return self.sinal

    # Demodulação Manchester: compara as duas metades de cada bit
    def demodular_manchester(self, sinal_str):
        amostras = [float(x) for x in sinal_str.split(',')]
        bits = ''
        for i in range(0, len(amostras) - 1, 2):
            # 0 -> [A,-A] (1a metade maior); 1 -> [-A,A] (2a metade maior)
            bits += '0' if amostras[i] > amostras[i+1] else '1'
        return bits

    # Modulação Bipolar: alterna +A/-A para bits '1', e usa 0 para '0'
    def bipolar(self, bits, A=1):
        sinal = []
        last = -A
        for b in bits:
            if b == '0':
                sinal.append(0)
            else:
                last = -last
                sinal.append(last)
        self.sinal = sinal
        return self.sinal

    # Demodulação Bipolar: |x| acima do limiar vira '1', perto de zero vira '0'
    def demodular_bipolar(self, sinal_str, A=1):
        amostras = [float(x) for x in sinal_str.split(',')]
        limiar = A / 2
        bits = ''.join(['1' if abs(x) > limiar else '0' for x in amostras])
        return bits

    # Modulação 32-QAM: cada 5 bits viram 1 ponto (I, Q) do tabuleiro.
    # I é a força do cosseno e Q a força do seno; somados formam o símbolo.
    def qam32(self, bits, A=1, f=5, fs=100):
        while len(bits) % 5 != 0:
            bits += '0'  # completa com zeros até ter múltiplo de 5
        t = np.linspace(0, 1, fs, endpoint=False)
        sinal = []
        for i in range(0, len(bits), 5):
            I, Q = PONTOS_32QAM[bits[i:i+5]]
            sinal.extend(A * (I * np.cos(2 * np.pi * f * t) + Q * np.sin(2 * np.pi * f * t)))
        self.sinal = sinal
        self.tempo = np.linspace(0, len(bits) / 5, len(sinal), endpoint=False)
        return sinal

    # Demodulação 32-QAM: compara cada símbolo recebido com os 32 pontos possíveis
    # e escolhe o mais próximo (menor distância)
    def demodular_qam32(self, sinal, A=1, f=5, fs=100):
        t = np.linspace(0, 1, fs, endpoint=False)
        bits = ''
        for i in range(0, len(sinal) - fs + 1, fs):
            simbolo = np.array(sinal[i:i+fs])
            melhor_bits, menor_dist = '', np.inf
            for grupo, (I, Q) in PONTOS_32QAM.items():
                referencia = A * (I * np.cos(2 * np.pi * f * t) + Q * np.sin(2 * np.pi * f * t))
                dist = np.sum((simbolo - referencia) ** 2)
                if dist < menor_dist:
                    melhor_bits, menor_dist = grupo, dist
            bits += melhor_bits
        return bits

    # Modulação FSK: bit 0 → frequência f0, bit 1 → frequência f1
    def fsk(self, bits, f0=5, f1=10, fs=100, A=1):
        sinal = []
        for i, b in enumerate(bits):
            t_i = np.linspace(i, i + 1, fs)
            f = f1 if b == '1' else f0
            s = A * np.sin(2 * np.pi * f * t_i)
            sinal.extend(s)
        self.sinal = sinal
        self.tempo = np.linspace(0, len(bits), len(sinal))
        return self.sinal

    # Demodulação FSK: qual frequência teve maior correlação
    def demodular_fsk(self, sinal, f0=5, f1=10, fs=100):
        bits = ''
        bloco_size = fs
        for i in range(0, len(sinal), bloco_size):
            bloco = sinal[i:i+bloco_size]
            if len(bloco) < bloco_size:
                break
            t_i = np.linspace(0, 1, fs, endpoint=False)
            s_f0 = np.sin(2 * np.pi * f0 * t_i)
            s_f1 = np.sin(2 * np.pi * f1 * t_i)
            corr_f0 = np.dot(bloco, s_f0)
            corr_f1 = np.dot(bloco, s_f1)
            bits += '0' if abs(corr_f0) > abs(corr_f1) else '1'
        return bits

    # Modulação ASK: bit 1 → seno de amplitude A, bit 0 → silêncio
    def ask(self, bits, A=1.0, f=5, fs=40):
        sinal = []
        for i, b in enumerate(bits):
            t_i = np.linspace(i, i + 1, fs, endpoint=False)
            amp = A if b == '1' else 0
            s = amp * np.sin(2 * np.pi * f * t_i)
            sinal.extend(s)
        self.sinal = sinal
        self.tempo = np.linspace(0, len(bits), len(sinal))
        return self.sinal

    # Demodulação ASK: energia média acima de um limiar proporcional à amplitude
    def demodular_ask(self, sinal, A=1.0, fs=40):
        total_blocos = len(sinal) // fs
        sinal = sinal[:total_blocos * fs]
        limiar = A * 0.3
        bits = ''
        for i in range(0, len(sinal), fs):
            bloco = sinal[i:i+fs]
            media = sum(abs(x) for x in bloco) / fs
            bits += '1' if media > limiar else '0'
        return bits

    # Tabela do 8PSK: cada grupo de 3 bits vira uma das 8 fases (0°, 45°, ..., 315°).
    # A ordem segue o código Gray: fases vizinhas diferem em apenas 1 bit,
    # então se o ruído confundir uma fase com a vizinha, só 1 bit sai errado.
    FASES_8PSK = {
        '000': 0 * np.pi / 4,   # 0°
        '001': 1 * np.pi / 4,   # 45°
        '011': 2 * np.pi / 4,   # 90°
        '010': 3 * np.pi / 4,   # 135°
        '110': 4 * np.pi / 4,   # 180°
        '111': 5 * np.pi / 4,   # 225°
        '101': 6 * np.pi / 4,   # 270°
        '100': 7 * np.pi / 4,   # 315°
    }

    # Modulação 8PSK: cada 3 bits viram 1 símbolo (uma senoide com a fase da tabela)
    def psk(self, bits, A=1, f=5, fs=100):
        while len(bits) % 3 != 0:
            bits += '0'  # completa com zeros até ter múltiplo de 3
        t = np.linspace(0, 1, fs, endpoint=False)
        sinal = []
        for i in range(0, len(bits), 3):
            fase = self.FASES_8PSK[bits[i:i+3]]
            sinal.extend(A * np.sin(2 * np.pi * f * t + fase))
        self.sinal = sinal
        self.tempo = np.linspace(0, len(bits) / 3, len(sinal), endpoint=False)
        return sinal

    # Demodulação 8PSK: compara cada símbolo recebido com as 8 fases possíveis
    # e escolhe a mais parecida (maior correlação)
    def demodular_psk(self, sinal, A=1, f=5, fs=100):
        t = np.linspace(0, 1, fs, endpoint=False)
        bits = ''
        for i in range(0, len(sinal) - fs + 1, fs):
            simbolo = np.array(sinal[i:i+fs])
            melhor_bits, maior_corr = '', -np.inf
            for grupo, fase in self.FASES_8PSK.items():
                referencia = A * np.sin(2 * np.pi * f * t + fase)
                corr = np.dot(simbolo, referencia)
                if corr > maior_corr:
                    melhor_bits, maior_corr = grupo, corr
            bits += melhor_bits
        return bits

    # Meio de comunicação: soma a cada amostra (em volts) um ruído gaussiano n(media, desvio)
    def adicionar_ruido(self, sinal, media=0.0, desvio=0.0):
        ruido = np.random.normal(media, desvio, len(sinal))
        return list(np.array(sinal, dtype=float) + ruido)