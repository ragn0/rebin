import argparse
import json
from datetime import datetime, timezone
import time
import os
from utilities import resolve_binary_path
from pwn import process, context
from run import run_and_record
# Rende l'output di pwntools meno verboso
context.log_level = "error"




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

    p = process([binary_real])
    
    print(f"--- Inizio Output del Replay ---")
    # Stampa l'output iniziale registrato
    initial_output = p.recv().decode(errors='ignore')
    print(initial_output, end='')
    
    # Esegui gli input registrati
    for logged_input in log_data["inputs"]:
        input_data = logged_input["data"]
        print(f"\n> [INVIO]: {input_data.strip()}")
        
        p.send(input_data.encode())
        
        time.sleep(0.2)
        
        response = p.recv().decode(errors='ignore')
        print(response, end='')

    p.wait() # Aspetta che il processo termini
    print(f"\n--- Fine Output del Replay ---")
    try:
        code = p.poll()
    except Exception:
        code = None
    print(f"[*] Replay completato. Codice di uscita: {code}")
    p.close()


if __name__ == "__main__":
    # Gestione dei comandi da riga di comando
    parser = argparse.ArgumentParser(description="Harness per interagire, registrare e rigiocare sessioni con binari.")
    subparsers = parser.add_subparsers(dest='command', required=True, help='Scegli il comando da eseguire')

    # Comando 'run' per interagire e registrare
    parser_run = subparsers.add_parser('run', help='Avvia una sessione interattiva e la registra.')
    parser_run.add_argument('binary', help='Path del binario da eseguire.')

    # Comando 'replay' per rigiocare una sessione
    parser_replay = subparsers.add_parser('replay', help='Riproduce una sessione da un file di log.')
    parser_replay.add_argument('logfile', help='Path del file di log JSON da rigiocare.')
    
    args = parser.parse_args()

    # Esegui il comando scelto
    if args.command == 'run':
        run_and_record(args.binary)

    elif args.command == 'replay':
        replay_session(args.logfile)
