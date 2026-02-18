import os
import sys
import select
import termios
import shutil
from .utilities import resolve_binary_path
from pwn import *
import pty
from .logger import SessionLogger


# --- FUNZIONE PER INTERAGIRE E REGISTRARE ---
def run_and_record(binary_path):
    """
    Avvia un binario locale, permette l'interazione e salva un log della sessione.
    """
    # 1. PREPARAZIONE DEL LOGGER
    session = SessionLogger(
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
    master = None
    try:
        master, slave = pty.openpty()

        # Disabilita l'eco sul lato slave del pty facendo un and con
        # la maschera di termios.ECHO annullata dal bitwise NOT ~
        attrs = termios.tcgetattr(slave)
        attrs[3] = attrs[3] & ~termios.ECHO
        termios.tcsetattr(slave, termios.TCSANOW, attrs)

        # Forza il binario ad avere stdout/stderr non bufferizzati
        # se 'stdbuf' è disponibile sul sistema.
        cmd = [binary_real]
        stdbuf_path = shutil.which("stdbuf")
        if stdbuf_path is not None:
            cmd = [stdbuf_path, "-i0", "-o0", "-e0", binary_real]

        p = process(cmd, stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)

        print(f"[*] Processo '{binary_path}' avviato. Inserisci i comandi e premi Invio. Premi Ctrl+D per finire.")

        # 3.1 CICLO DI INTERAZIONE BASATO SU SELECT
        #     Usiamo select su stdin e sul master del pty:
        #     - se arriva output dal binario, lo stampiamo subito
        #     - se l'utente digita qualcosa, lo inoltriamo al binario
        stdin_fd = sys.stdin.fileno()
        fds = [master, stdin_fd]

        while True:
            # Lista per vedere quali processi sono pronti per la lettura
            rlist, _, _ = select.select(fds, [], [])

            # Output dal binario
            if master in rlist:
                try:
                    data = os.read(master, 4096)
                    if not data:
                        break
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                    session.record_output(data)
                except OSError:
                    break
            # Input dall'utente
            if stdin_fd in rlist:
                try:
                    user_bytes = os.read(stdin_fd, 4096)
                except OSError:
                    user_bytes = b""

                if not user_bytes:
                    print("\n[*] Sessione terminata dall'utente.")
                    break

                os.write(master, user_bytes)
                session.record_input(user_bytes)
    
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
        


