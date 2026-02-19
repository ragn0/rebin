import os
import sys
import select
import termios
import shutil
from .utilities import resolve_binary_path
from pwn import *
import pty
from .logger import SessionLogger

# Esegue un comando in sessione PTY tenendo traccia di input e output.
def _interactive_pty_session(cmd, session: SessionLogger, banner: str) -> None:
    p = None
    master = None
    try:
        master, slave = pty.openpty()

        # Disabilita l'eco sul lato slave del pty dove eseguiremo il programma.
        attrs = termios.tcgetattr(slave)
        attrs[3] = attrs[3] & ~termios.ECHO
        termios.tcsetattr(slave, termios.TCSANOW, attrs)

        session.add_arglist(list(cmd))
        p = process(list(cmd), stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)

        print(banner)

        stdin_fd = sys.stdin.fileno()
        fds = [master, stdin_fd]
        output_buf = bytearray()

        def flush_output():
            if output_buf:
                session.record_output(bytes(output_buf))
                output_buf.clear()

        while True:
            rlist, _, _ = select.select(fds, [], [])

            if master in rlist:
                try:
                    data = os.read(master, 4096)
                    if not data:
                        flush_output()
                        break
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
                    output_buf.extend(data)
                except OSError:
                    flush_output()
                    break

            if stdin_fd in rlist:
                try:
                    user_bytes = os.read(stdin_fd, 4096)
                except OSError:
                    user_bytes = b""

                if not user_bytes:
                    flush_output()
                    print("\n[*] Sessione terminata dall'utente.")
                    break

                flush_output()
                os.write(master, user_bytes)
                session.record_input(user_bytes)
    finally:
        if p is not None:
            try:
                p.close()
            except Exception as e:
                session.finalize(p.poll(), str(e))
            try:
                session.finalize(p.poll(), None)
            except Exception:
                session.finalize(p.poll(), None)
        else:
            session.finalize(None, "Processo non avviato")

# Interagisci e registra
def run_and_record(binary_path):
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
    # Forza stdout/stderr non bufferizzati se 'stdbuf' è disponibile.
    cmd = [binary_real]
    stdbuf_path = shutil.which("stdbuf")
    if stdbuf_path is not None:
        cmd = [stdbuf_path, "-i0", "-o0", "-e0", binary_real]
    else:
        print("[!] stdbuf not installed, please install it for better I/O handling.")

    _interactive_pty_session    (
        cmd=cmd,
        session=session,
        banner=f"[*] Processo '{binary_path}' avviato. Inserisci i comandi e premi Invio. Premi Ctrl+D per finire.",
    )

    # 4. SALVATAGGIO
    log_file = session.save()
    print(f"[*] Sessione salvata in: {log_file}", flush=True)

# Avvia GDB in modalita' interattiva su un binario locale e registra la sessione.
def gdb_and_record(binary_path: str) -> None:
    session = SessionLogger(binary_path=binary_path, metadata={"wrapper": "gdb"})

    binary_real = resolve_binary_path(binary_path)
    if not os.path.isfile(binary_real):
        print(f"[!] Errore: Il binario '{binary_path}' non esiste (risolto in '{binary_real}').", flush=True)
        return
    if not os.access(binary_real, os.X_OK):
        print(f"[!] Errore: Il file '{binary_real}' non è eseguibile (chmod +x).", flush=True)
        return

    cmd = ["gdb", "-q", "-ex", "set pagination off", "--args", binary_real]

    _interactive_pty_session(
        cmd=cmd,
        session=session,
        banner=f"[*] gdb avviato su '{binary_path}'. Tutto l'I/O (gdb + programma) verrà registrato. Ctrl+D per terminare.",
    )

    log_file = session.save()
    print(f"[*] Sessione salvata in: {log_file}", flush=True)