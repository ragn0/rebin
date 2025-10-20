import os
from utilities import resolve_binary_path
from pwn import process
import logger


# --- FUNZIONE PER INTERAGIRE E REGISTRARE ---
def run_and_record(binary_path):
    """
    Avvia un binario locale, permette l'interazione e salva un log della sessione.
    """
    # 1. PREPARAZIONE DEL LOGGER
    session = logger.SessionLogger(
            binary_path=binary_path
    )
    
    # 2. Risoluzione e validazione percorso binario
    #    Supporta percorsi assoluti, CWD, e path relativi alla root del progetto
    binary_real = resolve_binary_path(binary_path)

    if not os.path.isfile(binary_real):
        print(f"[!] Errore: Il binario '{binary_path}' non esiste (risolto in '{binary_real}').", flush=True)
        return
    if not os.access(binary_real, os.X_OK):
        print(f"[!] Errore: Il file '{binary_real}' non è eseguibile (chmod +x).", flush=True)
        return

    # 3. ESECUZIONE DEL PROCESSO
    p = None
    try:
        p = process([binary_real])
        print(f"[*] Processo '{binary_path}' avviato. Inserisci i comandi e premi Invio. Premi Ctrl+D per finire.")

        # Leggi e registra l'output iniziale
        initial_output = p.recv().decode(errors='ignore')
        if initial_output:
            print(initial_output, end='')
            session.record_output(initial_output.encode())
            # log_data["outputs"].append({"t": 0.0, "data": initial_output})
        
        # 3. CICLO DI INTERAZIONE
        while p.poll() is None:
            try:
                user_input = input().encode()
                p.sendline(user_input)
                session.record_input(user_input + b'\n')

                response = p.recv().decode(errors='ignore')
                print(response, end='')
                session.record_output(response.encode())
            except EOFError:
                print("\n[*] Sessione terminata dall'utente.")
                break
    
    finally:
        # 4. SALVATAGGIO
        if p is not None:
            try:
                p.close()
            except Exception as e:
                session.finalize(p.poll(), e.__str__()) 
            try:
                session.finalize(p.poll(), None) 
            except Exception:
                session.finalize(p.poll(), None) 
        else:
            session.finalize(None, "Processo non avviato")
        log_file = session.save()
        print(f"[*] Sessione salvata in: {log_file}", flush=True)   
        


