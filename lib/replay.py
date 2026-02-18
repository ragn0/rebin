import argparse
import json
from datetime import datetime, timezone
import time
import os
import sys
import select
import shutil
from .utilities import resolve_binary_path
from pwn import *
import pty


# --- FUNZIONE PER RIGIOCARE UNA SESSIONE ---
def replay_session(log_filename):
    """
    Legge un file di log JSON e riesegue la sequenza di input.
    """
    print(f"[*] Inizio replay della sessione dal file '{log_filename}'...")
    binary_path = None 
    try:
        with open(log_filename, 'r') as f:
            log_data = json.load(f)
    except FileNotFoundError:
        print(f"[!] Errore: File di log '{log_filename}' non trovato.")
        return
    except json.JSONDecodeError:
        print(f"[!] Errore: Il file '{log_filename}' non è un JSON valido.")
        return

    binary_path = log_data.get("target")
    if not binary_path:
        print("[!] Errore: Il file di log non specifica un 'target'.")
        return

    # Risolvi path come in run_and_record
    binary_real = resolve_binary_path(binary_path)

    if not os.path.isfile(binary_real):
        print(f"[!] Errore: Il binario per il replay '{binary_path}' non esiste (risolto in '{binary_real}').")
        return
    if not os.access(binary_real, os.X_OK):
        print(f"[!] Errore: Il file '{binary_real}' non è eseguibile (chmod +x).")
        return

    master, slave = pty.openpty()

    # Usa stdbuf per forzare stdout/stderr non bufferizzati
    cmd = [binary_real]
    stdbuf_path = shutil.which("stdbuf")
    if stdbuf_path is not None:
        cmd = [stdbuf_path, "-i0", "-o0", "-e0", binary_real]

    p = process(cmd, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    
    print(f"--- Inizio Output del Replay ---")

    # Leggi eventuale output iniziale
    while True:
        rlist, _, _ = select.select([master], [], [], 0.05)
        if master not in rlist:
            break
        data = os.read(master, 4096)
        if not data:
            break
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.flush()
    
    # Esegui gli input registrati
    for logged_input in log_data["inputs"]:
        input_data = logged_input["data"]
        print(f"\n> [INVIO]: {input_data.strip()}")
        
        os.write(master, input_data.encode())
        
        # Dopo ogni input, raccogli l'output 
        while True:
            rlist, _, _ = select.select([master], [], [], 0.1)
            if master not in rlist:
                break
            try:
                data = os.read(master, 4096)
                if not data:
                    break
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
            except OSError:
                break
    # Puliamo l'output residuo fino alla fine del processo
    p.wait()
    while True:
        rlist, _, _ = select.select([master], [], [], 0.1)
        if master not in rlist:
            break
        try:
            data = os.read(master, 4096)
            if not data:
                break
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
        except OSError:
            break
    print(f"\n--- Fine Output del Replay ---")
    try:
        code = p.poll()
    except Exception:
        code = None
    print(f"[*] Replay completato. Codice di uscita: {code}")
    p.close()
