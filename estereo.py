"""
estereo.py creado por martina vermiglio mas

descripción: módulo para la manipulación y codificación de ficheros de audio WAVE.
Permite extraer canales, generar señales estéreo a partir de mono, y codificar señales
estéreo en un formato empaquetado de 32 bits, y su decodificación.
"""

import struct as st

def estereo2mono(ficEste, ficMono, canal=2):
    """extrae un canal (o combinación) de un fichero estéreo a uno mono."""
    with open(ficEste, 'rb') as fpIn, open(ficMono, 'wb') as fpOut:
        # lectura Bloque 1: RIFF
        fmtRiff = '<4sI4s'
        chunkId, chunkSize, chunkFmt = st.unpack(fmtRiff, fpIn.read(st.calcsize(fmtRiff)))
        
        # lectura Bloque 2: fmt
        fmtSub1 = '<4sIHHIIHH'
        (subChunk1Id, subChunk1Size, audioFmt, numChannels, 
         sampleRate, byteRate, blockAlign, bitsPerSample) = st.unpack(fmtSub1, fpIn.read(st.calcsize(fmtSub1)))
        
        if numChannels != 2 or chunkFmt != b'WAVE':
            raise ValueError("el fichero de entrada debe ser estéreo y formato WAVE.")

        # lectura Bloque 3: data
        fmtSub2 = '<4sI'
        subChunk2Id, subChunk2Size = st.unpack(fmtSub2, fpIn.read(st.calcsize(fmtSub2)))
        
        # leer datos de audio
        numMuestras = int(subChunk2Size // (bitsPerSample // 8))
        fmtDatos = f"<{numMuestras}h"
        muestras = st.unpack(fmtDatos, fpIn.read(st.calcsize(fmtDatos)))

        # separar canales intercalados
        izq = muestras[0::2]
        der = muestras[1::2]

        if canal == 0:
            mono = izq
        elif canal == 1:
            mono = der
        elif canal == 2:
            mono = [(l + r) // 2 for l, r in zip(izq, der)]
        elif canal == 3:
            mono = [(l - r) // 2 for l, r in zip(izq, der)]
        else:
            raise ValueError("el canal especificado no es válido.")

        # escritura cabecera Mono
        bytesMuestra = bitsPerSample // 8
        nuevoSubChunk2Size = len(mono) * bytesMuestra
        nuevoChunkSize = 36 + nuevoSubChunk2Size

        fpOut.write(st.pack(fmtRiff, chunkId, nuevoChunkSize, chunkFmt))
        fpOut.write(st.pack(fmtSub1, subChunk1Id, subChunk1Size, audioFmt, 1, 
                            sampleRate, sampleRate * bytesMuestra, bytesMuestra, bitsPerSample))
        fpOut.write(st.pack(fmtSub2, subChunk2Id, nuevoSubChunk2Size))
        
        # escritura de datos
        fpOut.write(st.pack(f"<{len(mono)}h", *mono))

def mono2estereo(ficIzq, ficDer, ficEste):
    """
    junta dos ficheros mono en un único fichero estéreo.
    """
    with open(ficIzq, 'rb') as fpIzq, open(ficDer, 'rb') as fpDer, open(ficEste, 'wb') as fpOut:
        
        fmtRiff = '<4sI4s'
        fmtSub1 = '<4sIHHIIHH'
        fmtSub2 = '<4sI'

        # leer cabecera Izquierda
        chunkIdIzq, _, chunkFmtIzq = st.unpack(fmtRiff, fpIzq.read(st.calcsize(fmtRiff)))
        (_, sub1SizeIzq, audioFmtIzq, chIzq, sRateIzq, _, _, bpsIzq) = st.unpack(fmtSub1, fpIzq.read(st.calcsize(fmtSub1)))
        (_, sub2SizeIzq) = st.unpack(fmtSub2, fpIzq.read(st.calcsize(fmtSub2)))
        
        if chIzq != 1:
            raise ValueError("el fichero izquierdo no es mono.")
            
        muestrasIzq = st.unpack(f"<{int(sub2SizeIzq // (bpsIzq // 8))}h", fpIzq.read(sub2SizeIzq))

        # leer cabecera Derecha
        _, _, _ = st.unpack(fmtRiff, fpDer.read(st.calcsize(fmtRiff)))
        (_, _, _, chDer, sRateDer, _, _, bpsDer) = st.unpack(fmtSub1, fpDer.read(st.calcsize(fmtSub1)))
        (_, sub2SizeDer) = st.unpack(fmtSub2, fpDer.read(st.calcsize(fmtSub2)))
        
        if chDer != 1 or sRateIzq != sRateDer:
            raise ValueError("el fichero derecho no es mono o difiere en frecuencia.")

        muestrasDer = st.unpack(f"<{int(sub2SizeDer // (bpsDer // 8))}h", fpDer.read(sub2SizeDer))

def codEstereo(ficEste, ficCod):
    """
    codifica estéreo de 16 bits en mono de 32 bits.
    """
    with open(ficEste, 'rb') as fpIn, open(ficCod, 'wb') as fpOut:
        fmtRiff = '<4sI4s'
        chunkId, _, chunkFmt = st.unpack(fmtRiff, fpIn.read(12))
        
        fmtSub1 = '<4sIHHIIHH'
        (sub1Id, sub1Size, aFmt, ch, sRate, _, _, bps) = st.unpack(fmtSub1, fpIn.read(24))
        
        if ch != 2:
            raise ValueError("se requiere un fichero estéreo para codificar.")

        fmtSub2 = '<4sI'
        sub2Id, sub2Size = st.unpack(fmtSub2, fpIn.read(8))
        
        numMuestras = sub2Size // (bps // 8)
        muestras = st.unpack(f"<{numMuestras}h", fpIn.read(sub2Size))

        izq = muestras[0::2]
        der = muestras[1::2]

        # codificamos aplicando desplazamientos de bits y máscaras
        codificado = [(((l + r) // 2 & 0xFFFF) << 16) | (((l - r) // 2) & 0xFFFF) for l, r in zip(izq, der)]

        # escribimos cabecera para 32 bits (4 bytes por muestra)
        nuevoSubChunk2Size = len(codificado) * 4
        nuevoChunkSize = 36 + nuevoSubChunk2Size

        fpOut.write(st.pack(fmtRiff, chunkId, nuevoChunkSize, chunkFmt))
        fpOut.write(st.pack(fmtSub1, sub1Id, sub1Size, aFmt, 1, sRate, sRate * 4, 4, 32))
        fpOut.write(st.pack(fmtSub2, sub2Id, nuevoSubChunk2Size))
        
        # guardamos como enteros sin signo ('I')
        fpOut.write(st.pack(f"<{len(codificado)}I", *codificado))

def decEstereo(ficCod, ficEste):
    """decodifica el fichero de 32 bits para recuperar el estéreo original."""
    with open(ficCod, 'rb') as fpIn, open(ficEste, 'wb') as fpOut:
        fmtRiff = '<4sI4s'
        chunkId, _, chunkFmt = st.unpack(fmtRiff, fpIn.read(12))
        
        fmtSub1 = '<4sIHHIIHH'
        (sub1Id, sub1Size, aFmt, ch, sRate, _, _, bps) = st.unpack(fmtSub1, fpIn.read(24))
        
        if bps != 32:
            raise ValueError("el fichero debe estar codificado en 32 bits.")

        fmtSub2 = '<4sI'
        sub2Id, sub2Size = st.unpack(fmtSub2, fpIn.read(8))
        
        numMuestras = sub2Size // 4
        muestras32 = st.unpack(f"<{numMuestras}I", fpIn.read(sub2Size))

        # reconstrucción combinando extracción por bits y asignación manual
        estereo = []
        for valor32 in muestras32:
            suma = (valor32 >> 16) & 0xFFFF
            diferencia = valor32 & 0xFFFF

            # recuperar signo negativo de 16 bits usando la lógica del complemento a 2
            if suma >= 0x8000:
                suma -= 0x10000
            if diferencia >= 0x8000:
                diferencia -= 0x10000

            estereo.append(suma + diferencia)  # canal izquierdo
            estereo.append(suma - diferencia)  # canal derecho

        nuevoSubChunk2Size = len(estereo) * 2
        nuevoChunkSize = 36 + nuevoSubChunk2Size

        fpOut.write(st.pack(fmtRiff, chunkId, nuevoChunkSize, chunkFmt))
        fpOut.write(st.pack(fmtSub1, sub1Id, sub1Size, aFmt, 2, sRate, sRate * 4, 4, 16))
        fpOut.write(st.pack(fmtSub2, sub2Id, nuevoSubChunk2Size))
        
        fpOut.write(st.pack(f"<{len(estereo)}h", *estereo))
