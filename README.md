## ReBin — play & replay di binari

Tool Python per **interagire con un binario**, registrare **input/output** in un file JSON, e poi **riprodurre (replay)** la stessa sessione.

### Requisiti

- **Python 3**
- **pwntools** (`pwn`)
- **`stdbuf`**: se presente, viene usato automaticamente per forzare stdout/stderr non bufferizzati e mostrare subito i prompt anche quando il binario non fa `fflush()` / `setvbuf()`.

### Come si usa

Il programma principale è `harness.py` e supporta due comandi:

- **play/record (run)**: avvia il binario in un pseudo-terminale, lascia interagire l’utente e salva un log JSON.

```bash
python3 harness.py run <path_al_binario>
```

- **replay**: rilegge un file JSON e reinvia gli input registrati, mostrando l’output risultante.

```bash
python3 harness.py replay <path_al_log_json>
```

### Output e log

- I log vengono salvati in `./sessions/` come `session_YYYY_MM_DD__HH_MM_SS.json`.
- Nel JSON trovi:
  - `target`: binario eseguito
  - `inputs`: lista degli input inviati (con timestamp relativo)
  - `outputs`: lista dell’output catturato (con timestamp relativo)
  - `exit_code` / `error`: info di terminazione

### Note pratiche

- L’interazione avviene tramite **PTY**
- Se un binario stampa senza newline (es. `printf("Prompt: ");`) e non fa flush, l’output può rimanere bufferizzato nella libc; quando disponibile, `stdbuf` risolve forzando `-o0 -e0`.

