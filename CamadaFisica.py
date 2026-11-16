"""
CamadaFisica.py - Camada física do simulador (TR1 - UnB)

Transforma bits em sinal elétrico (no transmissor) e sinal elétrico em bits
(no receptor).

    Modulação digital (banda base):  NRZ-Polar, Manchester e Bipolar
    Modulação por portadora:         ASK, FSK, 8PSK e 32-QAM

Combinados usados em todo o arquivo:
    - "bits" é uma string, por exemplo '0110'
    - "sinal" é uma lista de tensões em volts (uma tensão por amostra)
    - o tempo é contado em períodos de bit: cada bit dura AMOSTRAS_POR_BIT amostras
    - a frequência da portadora é dada em ciclos por período de bit

Seguindo a Figura 1 do enunciado, o modulador recebe o sinal NRZ que sai do
codificador banda base, e o demodulador devolve um sinal NRZ para o
decodificador banda base.
"""

import math


AMOSTRAS_POR_BIT = 40

# Nomes das opções (a interface gráfica mostra exatamente estes textos)
MODULACOES_DIGITAIS = ['NRZ-Polar', 'Manchester', 'Bipolar']
SEM_PORTADORA = 'Nenhuma (banda base)'
MODULACOES_POR_PORTADORA = [SEM_PORTADORA, 'ASK', 'FSK', '8PSK', '32-QAM']


# =============================================================================
# Funções auxiliares
# =============================================================================

def _media(valores):
    """Média aritmética de uma lista de números."""
    if len(valores) == 0:
        return 0.0
    return sum(valores) / len(valores)


def _angulo_da_portadora(frequencia, numero_da_amostra):
    """Ângulo (em radianos) da portadora em uma amostra: 2 * pi * f * t."""
    tempo = numero_da_amostra / AMOSTRAS_POR_BIT
    return 2 * math.pi * frequencia * tempo


def _medir_seno(amostras, frequencia):
    """Mede a amplitude do seno de uma frequência que existe dentro do trecho.

    Multiplica cada amostra pelo seno de referência e tira a média. Tudo que
    não for esse seno (outra frequência, cosseno, ruído) tende a se cancelar.
    """
    soma = 0.0
    for n in range(len(amostras)):
        soma += amostras[n] * math.sin(_angulo_da_portadora(frequencia, n))
    return 2 * soma / len(amostras)


def _medir_cosseno(amostras, frequencia):
    """Igual a _medir_seno, mas mede a amplitude do cosseno."""
    soma = 0.0
    for n in range(len(amostras)):
        soma += amostras[n] * math.cos(_angulo_da_portadora(frequencia, n))
    return 2 * soma / len(amostras)


# =============================================================================
# Modulação digital (banda base)
# =============================================================================

def codificar_nrz_polar(bits, amplitude):
    """NRZ-Polar: bit 1 vira +A volts e bit 0 vira -A volts."""
    sinal = []
    for bit in bits:
        if bit == '1':
            nivel = amplitude
        else:
            nivel = -amplitude
        for _ in range(AMOSTRAS_POR_BIT):
            sinal.append(nivel)
    return sinal


def decodificar_nrz_polar(sinal):
    """Média das amostras de cada bit: positiva vira 1, negativa vira 0."""
    bits = ''
    for inicio in range(0, len(sinal), AMOSTRAS_POR_BIT):
        amostras_do_bit = sinal[inicio:inicio + AMOSTRAS_POR_BIT]
        if _media(amostras_do_bit) >= 0:
            bits += '1'
        else:
            bits += '0'
    return bits


def codificar_manchester(bits, amplitude):
    """Manchester: todo bit tem uma transição no meio do seu período.

    bit 0 = primeira metade em +A e segunda metade em -A
    bit 1 = primeira metade em -A e segunda metade em +A
    """
    metade = AMOSTRAS_POR_BIT // 2
    sinal = []
    for bit in bits:
        if bit == '0':
            nivel_da_primeira_metade = amplitude
        else:
            nivel_da_primeira_metade = -amplitude
        for _ in range(metade):
            sinal.append(nivel_da_primeira_metade)
        for _ in range(metade):
            sinal.append(-nivel_da_primeira_metade)
    return sinal


def decodificar_manchester(sinal):
    """Compara as duas metades de cada bit: se a primeira é a maior, o bit é 0."""
    metade = AMOSTRAS_POR_BIT // 2
    bits = ''
    for inicio in range(0, len(sinal), AMOSTRAS_POR_BIT):
        primeira_metade = sinal[inicio:inicio + metade]
        segunda_metade = sinal[inicio + metade:inicio + AMOSTRAS_POR_BIT]
        if _media(primeira_metade) > _media(segunda_metade):
            bits += '0'
        else:
            bits += '1'
    return bits


def codificar_bipolar(bits, amplitude):
    """Bipolar (AMI): bit 0 vira 0 volts; os bits 1 alternam entre +A e -A."""
    sinal = []
    nivel_do_proximo_um = amplitude
    for bit in bits:
        if bit == '1':
            nivel = nivel_do_proximo_um
            nivel_do_proximo_um = -nivel_do_proximo_um
        else:
            nivel = 0.0
        for _ in range(AMOSTRAS_POR_BIT):
            sinal.append(nivel)
    return sinal


def decodificar_bipolar(sinal, amplitude):
    """Tensão longe de zero (para cima ou para baixo) é bit 1; perto de zero é bit 0."""
    limiar = amplitude / 2
    bits = ''
    for inicio in range(0, len(sinal), AMOSTRAS_POR_BIT):
        amostras_do_bit = sinal[inicio:inicio + AMOSTRAS_POR_BIT]
        if abs(_media(amostras_do_bit)) > limiar:
            bits += '1'
        else:
            bits += '0'
    return bits


def codificar_banda_base(bits, tipo, amplitude):
    """Chama o codificador banda base escolhido na interface."""
    if tipo == 'NRZ-Polar':
        return codificar_nrz_polar(bits, amplitude)
    if tipo == 'Manchester':
        return codificar_manchester(bits, amplitude)
    if tipo == 'Bipolar':
        return codificar_bipolar(bits, amplitude)
    raise ValueError('Modulação digital desconhecida: ' + tipo)


def decodificar_banda_base(sinal, tipo, amplitude):
    """Chama o decodificador banda base escolhido na interface."""
    if tipo == 'NRZ-Polar':
        return decodificar_nrz_polar(sinal)
    if tipo == 'Manchester':
        return decodificar_manchester(sinal)
    if tipo == 'Bipolar':
        return decodificar_bipolar(sinal, amplitude)
    raise ValueError('Modulação digital desconhecida: ' + tipo)


# =============================================================================
# Modulação por portadora: ASK e FSK (1 bit por símbolo)
# =============================================================================

def modular_ask(sinal_nrz, amplitude, frequencia):
    """ASK: bit 1 = portadora com amplitude A; bit 0 = sem portadora (0 volts)."""
    bits = decodificar_nrz_polar(sinal_nrz)
    sinal = []
    for bit in bits:
        if bit == '1':
            amplitude_do_bit = amplitude
        else:
            amplitude_do_bit = 0.0
        for n in range(AMOSTRAS_POR_BIT):
            angulo = _angulo_da_portadora(frequencia, n)
            sinal.append(amplitude_do_bit * math.sin(angulo))
    return sinal


def demodular_ask(sinal, amplitude, frequencia):
    """Mede a amplitude da portadora em cada bit: acima de A/2 é 1, abaixo é 0."""
    limiar = amplitude / 2
    bits = ''
    for inicio in range(0, len(sinal), AMOSTRAS_POR_BIT):
        amostras_do_bit = sinal[inicio:inicio + AMOSTRAS_POR_BIT]
        if _medir_seno(amostras_do_bit, frequencia) > limiar:
            bits += '1'
        else:
            bits += '0'
    return codificar_nrz_polar(bits, amplitude)


def modular_fsk(sinal_nrz, amplitude, frequencia):
    """FSK: bit 0 = portadora na frequência f; bit 1 = portadora no dobro (2f)."""
    bits = decodificar_nrz_polar(sinal_nrz)
    sinal = []
    for bit in bits:
        if bit == '1':
            frequencia_do_bit = 2 * frequencia
        else:
            frequencia_do_bit = frequencia
        for n in range(AMOSTRAS_POR_BIT):
            angulo = _angulo_da_portadora(frequencia_do_bit, n)
            sinal.append(amplitude * math.sin(angulo))
    return sinal


def demodular_fsk(sinal, amplitude, frequencia):
    """Mede as duas frequências em cada bit e fica com a que estiver mais forte."""
    bits = ''
    for inicio in range(0, len(sinal), AMOSTRAS_POR_BIT):
        amostras_do_bit = sinal[inicio:inicio + AMOSTRAS_POR_BIT]
        forca_do_zero = _medir_seno(amostras_do_bit, frequencia)
        forca_do_um = _medir_seno(amostras_do_bit, 2 * frequencia)
        if forca_do_um > forca_do_zero:
            bits += '1'
        else:
            bits += '0'
    return codificar_nrz_polar(bits, amplitude)


# =============================================================================
# Modulação por portadora: 8PSK e 32-QAM (vários bits por símbolo)
#
# Nas duas técnicas cada grupo de bits vira um ponto (I, Q) de uma tabela
# chamada constelação. O símbolo transmitido é:
#
#     tensão = A * (I * cosseno + Q * seno)
#
# No 8PSK os pontos ficam em um círculo (só a fase muda). No 32-QAM eles
# ficam em uma grade (amplitude e fase mudam).
# =============================================================================

BITS_POR_SIMBOLO_8PSK = 3
BITS_POR_SIMBOLO_32QAM = 5


def _montar_constelacao_8psk():
    """Tabela do 8PSK: cada grupo de 3 bits escolhe uma de 8 fases (0°, 45°, ..., 315°).

    A ordem dos grupos segue o código Gray: fases vizinhas diferem em 1 bit.
    Assim, se o ruído trocar uma fase pela vizinha, só 1 bit sai errado.
    """
    grupos_em_ordem_gray = ['000', '001', '011', '010', '110', '111', '101', '100']
    constelacao = {}
    for posicao in range(8):
        fase = posicao * (2 * math.pi / 8)
        grupo = grupos_em_ordem_gray[posicao]
        constelacao[grupo] = (math.cos(fase), math.sin(fase))
    return constelacao


def _montar_constelacao_32qam():
    """Tabela do 32-QAM: grade 6 x 6 de pontos (I, Q) sem os 4 cantos = 32 pontos.

    Os cantos ficam de fora porque são os pontos mais distantes do centro e
    gastariam mais energia. As coordenadas são divididas pela distância do
    ponto mais afastado, para o pico do sinal ser a amplitude A escolhida.
    """
    niveis = [-5, -3, -1, 1, 3, 5]
    maior_distancia = math.sqrt(5 ** 2 + 3 ** 2)
    constelacao = {}
    numero_do_ponto = 0
    for q in niveis:
        for i in niveis:
            eh_canto = abs(i) == 5 and abs(q) == 5
            if not eh_canto:
                grupo = format(numero_do_ponto, '05b')
                constelacao[grupo] = (i / maior_distancia, q / maior_distancia)
                numero_do_ponto += 1
    return constelacao


CONSTELACAO_8PSK = _montar_constelacao_8psk()
CONSTELACAO_32QAM = _montar_constelacao_32qam()


def _grupo_mais_proximo(i_medido, q_medido, constelacao):
    """Procura na constelação o ponto mais perto do ponto medido e devolve seus bits."""
    melhor_grupo = ''
    menor_distancia = None
    for grupo in constelacao:
        i, q = constelacao[grupo]
        distancia = (i_medido - i) ** 2 + (q_medido - q) ** 2
        if menor_distancia is None or distancia < menor_distancia:
            melhor_grupo = grupo
            menor_distancia = distancia
    return melhor_grupo


def _modular_com_constelacao(sinal_nrz, constelacao, bits_por_simbolo, amplitude, frequencia):
    """Transforma cada grupo de bits no símbolo A * (I * cosseno + Q * seno)."""
    bits = decodificar_nrz_polar(sinal_nrz)

    # completa com zeros até fechar o último símbolo
    while len(bits) % bits_por_simbolo != 0:
        bits += '0'

    amostras_por_simbolo = bits_por_simbolo * AMOSTRAS_POR_BIT
    sinal = []
    for inicio in range(0, len(bits), bits_por_simbolo):
        grupo = bits[inicio:inicio + bits_por_simbolo]
        i, q = constelacao[grupo]
        for n in range(amostras_por_simbolo):
            angulo = _angulo_da_portadora(frequencia, n)
            sinal.append(amplitude * (i * math.cos(angulo) + q * math.sin(angulo)))
    return sinal


def _demodular_com_constelacao(sinal, constelacao, bits_por_simbolo, amplitude, frequencia):
    """Mede o ponto (I, Q) de cada símbolo e escolhe o ponto mais próximo da tabela."""
    amostras_por_simbolo = bits_por_simbolo * AMOSTRAS_POR_BIT
    bits = ''
    for inicio in range(0, len(sinal), amostras_por_simbolo):
        amostras_do_simbolo = sinal[inicio:inicio + amostras_por_simbolo]
        i_medido = _medir_cosseno(amostras_do_simbolo, frequencia) / amplitude
        q_medido = _medir_seno(amostras_do_simbolo, frequencia) / amplitude
        bits += _grupo_mais_proximo(i_medido, q_medido, constelacao)
    return codificar_nrz_polar(bits, amplitude)


def modular_8psk(sinal_nrz, amplitude, frequencia):
    """8PSK: cada 3 bits viram 1 símbolo; a informação está na fase da portadora."""
    return _modular_com_constelacao(sinal_nrz, CONSTELACAO_8PSK,
                                    BITS_POR_SIMBOLO_8PSK, amplitude, frequencia)


def demodular_8psk(sinal, amplitude, frequencia):
    """Recupera 3 bits de cada símbolo 8PSK."""
    return _demodular_com_constelacao(sinal, CONSTELACAO_8PSK,
                                      BITS_POR_SIMBOLO_8PSK, amplitude, frequencia)


def modular_32qam(sinal_nrz, amplitude, frequencia):
    """32-QAM: cada 5 bits viram 1 símbolo; a informação está na amplitude e na fase."""
    return _modular_com_constelacao(sinal_nrz, CONSTELACAO_32QAM,
                                    BITS_POR_SIMBOLO_32QAM, amplitude, frequencia)


def demodular_32qam(sinal, amplitude, frequencia):
    """Recupera 5 bits de cada símbolo 32-QAM."""
    return _demodular_com_constelacao(sinal, CONSTELACAO_32QAM,
                                      BITS_POR_SIMBOLO_32QAM, amplitude, frequencia)


def modular(sinal_nrz, tipo, amplitude, frequencia):
    """Chama o modulador escolhido na interface. Entra NRZ, sai o sinal modulado."""
    if tipo == 'ASK':
        return modular_ask(sinal_nrz, amplitude, frequencia)
    if tipo == 'FSK':
        return modular_fsk(sinal_nrz, amplitude, frequencia)
    if tipo == '8PSK':
        return modular_8psk(sinal_nrz, amplitude, frequencia)
    if tipo == '32-QAM':
        return modular_32qam(sinal_nrz, amplitude, frequencia)
    raise ValueError('Modulação por portadora desconhecida: ' + tipo)


def demodular(sinal, tipo, amplitude, frequencia):
    """Chama o demodulador escolhido na interface. Entra o sinal modulado, sai NRZ."""
    if tipo == 'ASK':
        return demodular_ask(sinal, amplitude, frequencia)
    if tipo == 'FSK':
        return demodular_fsk(sinal, amplitude, frequencia)
    if tipo == '8PSK':
        return demodular_8psk(sinal, amplitude, frequencia)
    if tipo == '32-QAM':
        return demodular_32qam(sinal, amplitude, frequencia)
    raise ValueError('Modulação por portadora desconhecida: ' + tipo)
