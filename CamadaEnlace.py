"""
CamadaEnlace.py - Camada de enlace do simulador (TR1 - UnB)

    1. Enquadramento: contagem de caracteres, entrelaçamento de bits,
       flags com inserção de bytes e flags com inserção de bits
    2. Detecção de erros: bit de paridade par, checksum e CRC-32
    3. Correção de erros: código de Hamming

Todos os dados deste arquivo são strings de bits, por exemplo '01101001'.
Nenhuma biblioteca externa é usada: todos os cálculos são feitos aqui.
"""

BITS_POR_BYTE = 8

FLAG = '01111110'   # byte 0x7E: marca o início e o fim do quadro
ESC = '01111101'    # byte 0x7D: avisa que o próximo byte é dado, e não uma FLAG

# Polinômio gerador CRC-32 do padrão IEEE 802 (33 bits, grau 32)
POLINOMIO_CRC32 = '100000100110000010001110110110111'
TAMANHO_DO_CRC = 32

# Hamming(7,4): blocos de 7 bits com 4 bits de dados e 3 de paridade.
# As paridades ficam nas posições que são potências de 2.
DADOS_POR_BLOCO_HAMMING = 4
TAMANHO_DO_BLOCO_HAMMING = 7
POSICOES_DE_PARIDADE_HAMMING = [1, 2, 4]

# Nomes das opções (a interface gráfica mostra exatamente estes textos)
TIPOS_DE_ENQUADRAMENTO = ['Contagem de caracteres', 'Entrelaçamento de bits',
                          'Flags e inserção de bytes', 'Flags e inserção de bits']
TIPOS_DE_EDC = ['Bit de paridade par', 'Checksum', 'CRC-32', 'Hamming']
TAMANHOS_DE_CHECKSUM = [8, 16, 32]


def _numero_para_bits(numero, quantidade_de_bits):
    """Escreve um número em binário com a quantidade de bits pedida (zeros à esquerda)."""
    return format(numero, 'b').zfill(quantidade_de_bits)


# =============================================================================
# 1. Enquadramento
#
# As funções "enquadrar" recebem os bits da aplicação e devolvem o quadro.
# As funções "desenquadrar" devolvem dois valores: os dados e um aviso.
# O aviso é um texto vazio quando o quadro chegou com a estrutura correta.
# =============================================================================

def enquadrar_contagem(dados):
    """Contagem de caracteres: um cabeçalho de 8 bits diz quantos bytes de dados vêm depois."""
    quantidade_de_bytes = len(dados) // BITS_POR_BYTE
    cabecalho = _numero_para_bits(quantidade_de_bytes, BITS_POR_BYTE)
    return cabecalho + dados


def desenquadrar_contagem(quadro):
    """Lê o cabeçalho e separa a quantidade de bytes que ele anuncia."""
    if len(quadro) < BITS_POR_BYTE:
        return '', 'o quadro é menor que o cabeçalho'

    quantidade_de_bytes = int(quadro[:BITS_POR_BYTE], 2)
    fim_dos_dados = BITS_POR_BYTE + quantidade_de_bytes * BITS_POR_BYTE
    dados = quadro[BITS_POR_BYTE:fim_dos_dados]

    aviso = ''
    if len(quadro) < fim_dos_dados:
        aviso = 'o cabeçalho anuncia mais bytes do que os que chegaram'
    return dados, aviso


def _paridade_das_colunas(dados):
    """Paridade par de cada uma das 8 colunas (cada byte dos dados é uma linha)."""
    paridade = ''
    for coluna in range(BITS_POR_BYTE):
        quantidade_de_uns = 0
        for inicio_da_linha in range(0, len(dados), BITS_POR_BYTE):
            if dados[inicio_da_linha + coluna] == '1':
                quantidade_de_uns += 1
        if quantidade_de_uns % 2 == 0:
            paridade += '0'
        else:
            paridade += '1'
    return paridade


def enquadrar_entrelacamento(dados):
    """Entrelaçamento de bits: os dados formam uma matriz com 1 byte por linha.

    O quadro leva um cabeçalho com o número de linhas, os dados linha por linha
    e, no fim, uma linha extra com a paridade par de cada coluna. Um erro em
    rajada de até 8 bits atinge colunas diferentes e por isso é percebido.
    """
    quantidade_de_linhas = len(dados) // BITS_POR_BYTE
    cabecalho = _numero_para_bits(quantidade_de_linhas, BITS_POR_BYTE)
    return cabecalho + dados + _paridade_das_colunas(dados)


def desenquadrar_entrelacamento(quadro):
    """Separa os dados e confere a linha de paridade das colunas."""
    if len(quadro) < BITS_POR_BYTE:
        return '', 'o quadro é menor que o cabeçalho'

    quantidade_de_linhas = int(quadro[:BITS_POR_BYTE], 2)
    fim_dos_dados = BITS_POR_BYTE + quantidade_de_linhas * BITS_POR_BYTE
    fim_da_paridade = fim_dos_dados + BITS_POR_BYTE
    dados = quadro[BITS_POR_BYTE:fim_dos_dados]
    paridade_recebida = quadro[fim_dos_dados:fim_da_paridade]

    aviso = ''
    if len(quadro) < fim_da_paridade:
        aviso = 'o cabeçalho anuncia mais linhas do que as que chegaram'
    elif _paridade_das_colunas(dados) != paridade_recebida:
        aviso = 'a paridade das colunas não confere'
    return dados, aviso


def enquadrar_insercao_de_bytes(dados):
    """Flags e inserção de bytes: o quadro começa e termina com o byte FLAG.

    Se um byte dos dados for igual à FLAG ou ao ESC, um byte ESC é inserido
    antes dele, para o receptor não confundir esse dado com o fim do quadro.
    """
    quadro = FLAG
    for inicio in range(0, len(dados), BITS_POR_BYTE):
        byte = dados[inicio:inicio + BITS_POR_BYTE]
        if byte == FLAG or byte == ESC:
            quadro += ESC
        quadro += byte
    quadro += FLAG
    return quadro


def desenquadrar_insercao_de_bytes(quadro):
    """Lê byte a byte até achar a FLAG final, retirando os bytes ESC inseridos."""
    if quadro[:BITS_POR_BYTE] != FLAG:
        return '', 'a FLAG inicial não foi encontrada'

    dados = ''
    posicao = BITS_POR_BYTE
    while posicao + BITS_POR_BYTE <= len(quadro):
        byte = quadro[posicao:posicao + BITS_POR_BYTE]
        if byte == FLAG:
            return dados, ''
        if byte == ESC:
            # o ESC não é dado: pula para o byte seguinte, que é copiado como está
            posicao += BITS_POR_BYTE
            byte = quadro[posicao:posicao + BITS_POR_BYTE]
        dados += byte
        posicao += BITS_POR_BYTE
    return dados, 'a FLAG final não foi encontrada'


def enquadrar_insercao_de_bits(dados):
    """Flags e inserção de bits: depois de cinco bits 1 seguidos, um bit 0 é inserido.

    Assim a sequência da FLAG (seis bits 1 seguidos) nunca aparece no meio dos dados.
    """
    dados_com_insercao = ''
    uns_seguidos = 0
    for bit in dados:
        dados_com_insercao += bit
        if bit == '1':
            uns_seguidos += 1
        else:
            uns_seguidos = 0
        if uns_seguidos == 5:
            dados_com_insercao += '0'
            uns_seguidos = 0
    return FLAG + dados_com_insercao + FLAG


def desenquadrar_insercao_de_bits(quadro):
    """Localiza as duas FLAGs e retira o bit 0 inserido depois de cada cinco bits 1."""
    if quadro[:BITS_POR_BYTE] != FLAG:
        return '', 'a FLAG inicial não foi encontrada'

    posicao_da_flag_final = quadro.find(FLAG, BITS_POR_BYTE)
    if posicao_da_flag_final == -1:
        return '', 'a FLAG final não foi encontrada'

    dados_com_insercao = quadro[BITS_POR_BYTE:posicao_da_flag_final]
    dados = ''
    uns_seguidos = 0
    posicao = 0
    while posicao < len(dados_com_insercao):
        bit = dados_com_insercao[posicao]
        dados += bit
        if bit == '1':
            uns_seguidos += 1
        else:
            uns_seguidos = 0
        if uns_seguidos == 5:
            posicao += 1    # pula o bit 0 que o transmissor inseriu
            uns_seguidos = 0
        posicao += 1
    return dados, ''


def enquadrar(dados, tipo):
    """Chama o enquadramento escolhido na interface."""
    if tipo == 'Contagem de caracteres':
        return enquadrar_contagem(dados)
    if tipo == 'Entrelaçamento de bits':
        return enquadrar_entrelacamento(dados)
    if tipo == 'Flags e inserção de bytes':
        return enquadrar_insercao_de_bytes(dados)
    if tipo == 'Flags e inserção de bits':
        return enquadrar_insercao_de_bits(dados)
    raise ValueError('Tipo de enquadramento desconhecido: ' + tipo)


def desenquadrar(quadro, tipo):
    """Chama o desenquadramento escolhido na interface. Devolve (dados, aviso)."""
    if tipo == 'Contagem de caracteres':
        return desenquadrar_contagem(quadro)
    if tipo == 'Entrelaçamento de bits':
        return desenquadrar_entrelacamento(quadro)
    if tipo == 'Flags e inserção de bytes':
        return desenquadrar_insercao_de_bytes(quadro)
    if tipo == 'Flags e inserção de bits':
        return desenquadrar_insercao_de_bits(quadro)
    raise ValueError('Tipo de enquadramento desconhecido: ' + tipo)


# =============================================================================
# 2. Detecção de erros
#
# As funções "adicionar" anexam o código de verificação ao final do quadro.
# As funções "verificar" devolvem dois valores: o quadro sem o código e
# True/False dizendo se um erro foi detectado.
# =============================================================================

def adicionar_paridade(bits):
    """Bit de paridade par: anexa 1 bit para que o total de bits 1 fique par."""
    if bits.count('1') % 2 == 0:
        bit_de_paridade = '0'
    else:
        bit_de_paridade = '1'
    return bits + bit_de_paridade


def verificar_paridade(bits):
    """Se o total de bits 1 (contando o de paridade) for ímpar, houve erro."""
    erro_detectado = bits.count('1') % 2 != 0
    return bits[:-1], erro_detectado


def _soma_em_complemento_de_um(bits, tamanho):
    """Corta os bits em palavras de `tamanho` bits e soma todas elas.

    Quando a soma não cabe mais na palavra, o "vai um" que sobrou é somado de
    volta no bit menos significativo (soma em complemento de um).
    """
    # completa a última palavra com zeros, apenas para fazer a conta
    while len(bits) % tamanho != 0:
        bits += '0'

    maior_valor = 2 ** tamanho - 1    # palavra com todos os bits em 1
    soma = 0
    for inicio in range(0, len(bits), tamanho):
        palavra = int(bits[inicio:inicio + tamanho], 2)
        soma += palavra
        if soma > maior_valor:
            soma = soma - (maior_valor + 1)    # retira o "vai um" que passou do tamanho
            soma = soma + 1                    # e soma ele de volta no final
    return soma


def adicionar_checksum(bits, tamanho):
    """Checksum: soma as palavras do quadro e anexa o complemento de um da soma."""
    maior_valor = 2 ** tamanho - 1
    soma = _soma_em_complemento_de_um(bits, tamanho)
    checksum = maior_valor - soma    # inverte todos os bits da soma
    return bits + _numero_para_bits(checksum, tamanho)


def verificar_checksum(bits, tamanho):
    """Soma os dados com o checksum recebido: sem erro, o resultado é tudo 1."""
    if len(bits) <= tamanho:
        return '', True

    dados = bits[:-tamanho]
    checksum_recebido = int(bits[-tamanho:], 2)

    maior_valor = 2 ** tamanho - 1
    soma = _soma_em_complemento_de_um(dados, tamanho) + checksum_recebido
    if soma > maior_valor:
        soma = soma - (maior_valor + 1) + 1

    erro_detectado = soma != maior_valor
    return dados, erro_detectado


def _resto_da_divisao_crc(bits):
    """Divide os bits pelo polinômio gerador (divisão binária com XOR) e devolve o resto."""
    resto = list(bits)
    for posicao in range(len(bits) - TAMANHO_DO_CRC):
        # só "cabe" o divisor quando o bit mais à esquerda ainda é 1
        if resto[posicao] == '1':
            for k in range(len(POLINOMIO_CRC32)):
                if resto[posicao + k] == POLINOMIO_CRC32[k]:
                    resto[posicao + k] = '0'
                else:
                    resto[posicao + k] = '1'
    return ''.join(resto[-TAMANHO_DO_CRC:])


def adicionar_crc32(bits):
    """CRC-32: anexa o resto da divisão do quadro (seguido de 32 zeros) pelo gerador."""
    resto = _resto_da_divisao_crc(bits + '0' * TAMANHO_DO_CRC)
    return bits + resto


def verificar_crc32(bits):
    """Divide tudo que chegou pelo gerador: sem erro, o resto é zero."""
    if len(bits) <= TAMANHO_DO_CRC:
        return '', True

    resto = _resto_da_divisao_crc(bits)
    erro_detectado = '1' in resto
    return bits[:-TAMANHO_DO_CRC], erro_detectado


# =============================================================================
# 3. Correção de erros: Hamming(7,4)
#
# Cada bloco tem 7 posições, numeradas de 1 a 7:
#
#     posição:   1   2   3   4   5   6   7
#     conteúdo:  p1  p2  d1  p4  d2  d3  d4      (p = paridade, d = dado)
#
# Cada paridade cobre as posições cujo número, em binário, tem o bit dela:
#     p1 cobre 1, 3, 5, 7      p2 cobre 2, 3, 6, 7      p4 cobre 4, 5, 6, 7
# =============================================================================

def _paridade_hamming(bloco, paridade):
    """XOR de todas as posições do bloco cobertas por uma paridade (1, 2 ou 4)."""
    resultado = 0
    for posicao in range(1, TAMANHO_DO_BLOCO_HAMMING + 1):
        if posicao & paridade != 0:
            resultado = resultado ^ bloco[posicao]
    return resultado


def codificar_hamming(bits):
    """Transforma cada grupo de 4 bits de dados em um bloco de 7 bits."""
    # completa com zeros até fechar o último grupo de 4 bits
    while len(bits) % DADOS_POR_BLOCO_HAMMING != 0:
        bits += '0'

    codificado = ''
    for inicio in range(0, len(bits), DADOS_POR_BLOCO_HAMMING):
        dados = bits[inicio:inicio + DADOS_POR_BLOCO_HAMMING]

        # bloco[1] até bloco[7] são as posições; bloco[0] não é usado
        bloco = [0] * (TAMANHO_DO_BLOCO_HAMMING + 1)

        # os dados ocupam as posições que não são de paridade
        proximo_dado = 0
        for posicao in range(1, TAMANHO_DO_BLOCO_HAMMING + 1):
            if posicao not in POSICOES_DE_PARIDADE_HAMMING:
                bloco[posicao] = int(dados[proximo_dado])
                proximo_dado += 1

        for paridade in POSICOES_DE_PARIDADE_HAMMING:
            bloco[paridade] = _paridade_hamming(bloco, paridade)

        for posicao in range(1, TAMANHO_DO_BLOCO_HAMMING + 1):
            codificado += str(bloco[posicao])
    return codificado


def decodificar_hamming(bits):
    """Corrige até 1 bit errado por bloco. Devolve (dados, quantidade de bits corrigidos)."""
    dados = ''
    bits_corrigidos = 0
    quantidade_de_blocos = len(bits) // TAMANHO_DO_BLOCO_HAMMING
    for numero_do_bloco in range(quantidade_de_blocos):
        inicio = numero_do_bloco * TAMANHO_DO_BLOCO_HAMMING
        bloco = [0]
        for bit in bits[inicio:inicio + TAMANHO_DO_BLOCO_HAMMING]:
            bloco.append(int(bit))

        # somando as paridades que falharam, o resultado é a posição do bit errado
        posicao_do_erro = 0
        for paridade in POSICOES_DE_PARIDADE_HAMMING:
            if _paridade_hamming(bloco, paridade) != 0:
                posicao_do_erro += paridade

        if posicao_do_erro != 0:
            bloco[posicao_do_erro] = 1 - bloco[posicao_do_erro]    # inverte o bit errado
            bits_corrigidos += 1

        for posicao in range(1, TAMANHO_DO_BLOCO_HAMMING + 1):
            if posicao not in POSICOES_DE_PARIDADE_HAMMING:
                dados += str(bloco[posicao])
    return dados, bits_corrigidos


# =============================================================================
# Escolha do método de detecção ou correção (EDC)
# =============================================================================

def adicionar_edc(quadro, tipo, tamanho_do_checksum):
    """Transmissor: aplica o método de detecção ou correção escolhido na interface."""
    if tipo == 'Bit de paridade par':
        return adicionar_paridade(quadro)
    if tipo == 'Checksum':
        return adicionar_checksum(quadro, tamanho_do_checksum)
    if tipo == 'CRC-32':
        return adicionar_crc32(quadro)
    if tipo == 'Hamming':
        return codificar_hamming(quadro)
    raise ValueError('Tipo de detecção ou correção desconhecido: ' + tipo)


def verificar_edc(bits, tipo, tamanho_do_checksum):
    """Receptor: confere (ou corrige) o que chegou.

    Devolve três valores: o quadro sem o código, True/False dizendo se um erro
    foi detectado e a quantidade de bits corrigidos (só o Hamming corrige).
    """
    if tipo == 'Hamming':
        quadro, bits_corrigidos = decodificar_hamming(bits)
        return quadro, False, bits_corrigidos

    if tipo == 'Bit de paridade par':
        quadro, erro_detectado = verificar_paridade(bits)
    elif tipo == 'Checksum':
        quadro, erro_detectado = verificar_checksum(bits, tamanho_do_checksum)
    elif tipo == 'CRC-32':
        quadro, erro_detectado = verificar_crc32(bits)
    else:
        raise ValueError('Tipo de detecção ou correção desconhecido: ' + tipo)
    return quadro, erro_detectado, 0
