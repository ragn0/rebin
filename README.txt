================================================================================
SPIEGAZIONE DETTAGLIATA DEL FUNZIONAMENTO DEL PROGETTO ReBin
================================================================================

OVERVIEW GENERALE
================================================================================

ReBin è un tool Python che permette di:
1. Eseguire binari in modo interattivo tramite pseudo-terminale (PTY)
2. Registrare tutti gli input dell'utente e tutto l'output del programma
3. Salvare la sessione in un file JSON
4. Riprodurre (replay) la sessione registrata reinviando gli stessi input

Il progetto supporta tre modalità:
- Esecuzione diretta di un binario (comando 'run')
- Esecuzione tramite gdb per debugging (comando 'gdb')
- Riproduzione di una sessione salvata (comando 'replay')


ARCHITETTURA DEL PROGETTO
================================================================================

Il progetto è organizzato in moduli:

1. harness.py          - Entry point principale, gestisce CLI e routing comandi
2. lib/run.py          - Logica per esecuzione interattiva e registrazione
3. lib/replay.py       - Logica per riproduzione sessioni salvate
4. lib/logger.py       - Classe SessionLogger per gestione log JSON
5. lib/utilities.py    - Funzioni di utilità (path resolution, file I/O)


DETTAGLIO MODULO PER MODULO
================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. harness.py - Entry Point e CLI
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FUNZIONE: Gestisce l'interfaccia a riga di comando e instrada i comandi.

STRUTTURA:
- Usa argparse per creare un parser con subparsers per i tre comandi
- Imposta log_level di pwntools a "error" per ridurre verbosità
- Instrada a run_and_record(), gdb_and_record(), o replay_session()

FLUSSO:
1. Parse degli argomenti CLI
2. Identificazione del comando (run/gdb/replay)
3. Chiamata alla funzione corrispondente con i parametri


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
2. lib/run.py - Esecuzione Interattiva e Registrazione
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Questo modulo contiene la logica principale per eseguire binari e registrare
le sessioni. È composto da tre funzioni principali:

┌─────────────────────────────────────────────────────────────────────────────┐
│ _interactive_pty_session(cmd, session, banner)                             │
└─────────────────────────────────────────────────────────────────────────────┘

FUNZIONE: Funzione generica che esegue un comando arbitrario in un PTY e
          registra tutto l'I/O interattivo.

PARAMETRI:
- cmd: lista di stringhe rappresentante il comando da eseguire
- session: istanza di SessionLogger per registrare I/O
- banner: messaggio da stampare all'avvio

DETTAGLI TECNICI:

1. CREAZIONE PTY:
   - pty.openpty() crea una coppia master/slave di pseudo-terminali
   - Il processo viene eseguito con stdin/stdout/stderr collegati allo slave
   - Il master viene usato per leggere output e scrivere input

2. DISABILITAZIONE ECHO:
   - Usa termios per modificare gli attributi del terminale slave
   - Disabilita ECHO (bitwise AND con ~termios.ECHO) per evitare che l'input
     dell'utente venga rispedito indietro dal kernel
   - Questo elimina il problema dell'eco doppio dell'input

3. BUFFERING OUTPUT:
   - Usa un bytearray (output_buf) per accumulare output dal processo
   - L'output viene accumulato fino a quando:
     a) L'utente invia input → flush del buffer e registrazione come entry unica
     b) Il processo termina (EOF) → flush del buffer residuo
   - Questo permette di catturare output lunghi (es. disas main in gdb) come
     una singola entry nel log invece di molte piccole entry

4. LOOP PRINCIPALE CON select():
   - Usa select.select() per monitorare simultaneamente:
     * master (output dal processo)
     * stdin (input dall'utente)
   - Quando arriva output dal master:
     * Legge fino a 4096 byte
     * Stampa immediatamente a schermo (sys.stdout.buffer.write)
     * Accumula nel buffer (output_buf.extend)
   - Quando arriva input da stdin:
     * Flush del buffer output prima di registrare l'input
     * Scrive l'input sul master (os.write)
     * Registra l'input nel logger (session.record_input)

5. GESTIONE ERRORI:
   - Try/except per OSError durante lettura/scrittura
   - Finally block per cleanup: chiude processo e finalizza sessione


┌─────────────────────────────────────────────────────────────────────────────┐
│ run_and_record(binary_path)                                                │
└─────────────────────────────────────────────────────────────────────────────┘

FUNZIONE: Esegue un binario direttamente e registra la sessione.

FLUSSO:
1. Crea un SessionLogger con il path del binario
2. Risolve il path del binario usando resolve_binary_path() (supporta path
   relativi, assoluti, e relativi alla root del progetto)
3. Valida esistenza ed eseguibilità del binario
4. Costruisce il comando:
   - Se stdbuf è disponibile: ["stdbuf", "-i0", "-o0", "-e0", binary_real]
     * -i0: stdin non bufferizzato
     * -o0: stdout non bufferizzato
     * -e0: stderr non bufferizzato
   - Altrimenti: [binary_real]
5. Chiama _interactive_pty_session() con il comando costruito
6. Salva il log JSON e stampa il path del file


┌─────────────────────────────────────────────────────────────────────────────┐
│ gdb_and_record(binary_path)                                                │
└─────────────────────────────────────────────────────────────────────────────┘

FUNZIONE: Esegue un binario tramite gdb e registra la sessione.

DIFFERENZE RISPETTO A run_and_record:
- Crea SessionLogger con metadata={"wrapper": "gdb"}
- Costruisce comando: ["gdb", "-q", "-ex", "set pagination off", "--args", binary_real]
  * -q: quiet mode (meno output iniziale)
  * -ex "set pagination off": disabilita paginazione automatica
  * --args: passa il binario come argomento a gdb
- L'output catturato include sia i comandi/output di gdb che l'output del
  programma in debug (tutto passa dalla stessa PTY)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
3. lib/replay.py - Riproduzione Sessioni
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────────────────────┐
│ replay_session(log_filename)                                               │
└─────────────────────────────────────────────────────────────────────────────┘

FUNZIONE: Legge un file JSON di log e riproduce la sessione reinviando gli
          input registrati.

FLUSSO DETTAGLIATO:

1. CARICAMENTO LOG:
   - Apre e parsea il file JSON
   - Estrae "target" (path del binario originale)
   - Estrae "args" se presente (comando completo usato, es. per sessioni gdb)

2. COSTRUZIONE COMANDO:
   - Se "args" è presente nel log:
     * Usa quella commandline (per sessioni gdb o wrapper)
     * Best-effort: se l'ultimo argomento è un path relativo, prova a risolverlo
   - Se "args" non è presente (log vecchi):
     * Risolve il path del binario
     * Valida esistenza ed eseguibilità
     * Aggiunge stdbuf se disponibile (come in run_and_record)

3. ESECUZIONE E REPLAY:
   - Crea PTY e avvia il processo con il comando costruito
   - Legge output iniziale (con timeout 0.05s per non bloccare)
   - Per ogni input nel log:
     * Stampa un messaggio indicativo
     * Scrive l'input sul master del PTY (os.write)
     * Attende e legge l'output risultante (timeout 0.1s tra chunk)
   - Dopo tutti gli input, attende terminazione processo (p.wait())
   - Drena output residuo fino a EOF
   - Stampa codice di uscita e chiude


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
4. lib/logger.py - Gestione Log JSON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────────────────────┐
│ SessionLogger                                                               │
└─────────────────────────────────────────────────────────────────────────────┘

CLASSE: Gestisce la creazione, popolamento e salvataggio di log JSON.

STRUTTURA DEL LOG JSON:
{
  "id": "YYYYMMDD_HHMMSS",           // ID univoco basato su timestamp
  "target": "path/to/binary",         // Path del binario eseguito
  "timestamp": "ISO8601",              // Timestamp UTC
  "args": ["cmd", "arg1", ...],        // Commandline completa eseguita
  "env": {},                           // Variabili d'ambiente (non usato)
  "inputs": [                          // Lista input dell'utente
    {"t": 0.123, "data": "input1\n"},
    {"t": 1.456, "data": "input2\n"}
  ],
  "outputs": [                         // Lista output del processo
    {"t": 0.234, "data": "output1"},
    {"t": 1.567, "data": "output2"}
  ],
  "exit_code": 0,                      // Codice di uscita
  "error": null,                        // Eventuale errore
  "metadata": {                         // Metadati aggiuntivi
    "python_version": "...",
    "platform": "...",
    "wrapper": "gdb"  // Opzionale, solo per sessioni gdb
  }
}

METODI:

- __init__(binary_path, env, metadata):
  * Inizializza self.t0 con monotonic_s() (timestamp di riferimento)
  * Crea struttura log base con campi vuoti

- add_arglist(args):
  * Registra la commandline completa eseguita nel campo "args"

- record_input(data: bytes):
  * Aggiunge entry a "inputs" con timestamp relativo (monotonic_s() - self.t0)
  * Decodifica bytes in stringa (errors="ignore" per robustezza)

- record_output(data: bytes):
  * Aggiunge entry a "outputs" con timestamp relativo
  * Decodifica bytes in stringa

- finalize(exit_code, error):
  * Registra codice di uscita ed eventuale errore

- save(session_out=None):
  * Crea directory "sessions" se non esiste
  * Genera nome file con timestamp: session_YYYY_MM_DD__HH_MM_SS.json
  * Usa atomic_write_json() per scrittura atomica (evita corruzione)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
5. lib/utilities.py - Funzioni di Utilità
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌─────────────────────────────────────────────────────────────────────────────┐
│ resolve_binary_path(provided_path)                                          │
└─────────────────────────────────────────────────────────────────────────────┘

FUNZIONE: Risolve un path relativo in path assoluto, cercando in più location.

LOGICA:
1. Se il path è già assoluto → ritorna così com'è
2. Altrimenti prova in ordine:
   a) Path relativo alla directory corrente (os.path.abspath)
   b) Path relativo alla root del progetto (calcolata da __file__)
3. Se nessuno esiste, ritorna il path originale (sarà validato dopo)

UTILITÀ: Permette di specificare binari con path relativi senza dover essere
         nella directory corretta.


┌─────────────────────────────────────────────────────────────────────────────┐
│ monotonic_s()                                                                │
└─────────────────────────────────────────────────────────────────────────────┘

FUNZIONE: Wrapper per time.monotonic() che ritorna timestamp in secondi.

UTILITÀ: Timestamp monotonici (non retrocedono mai) per misurare durate
         relative accurate anche con aggiustamenti orologio di sistema.


┌─────────────────────────────────────────────────────────────────────────────┐
│ atomic_write_json(path, obj)                                                │
└─────────────────────────────────────────────────────────────────────────────┘

FUNZIONE: Scrive un oggetto Python come JSON in modo atomico.

TECNICA:
1. Scrive su file temporaneo (path.tmp)
2. Flush esplicito del buffer
3. fsync() per assicurare scrittura su disco
4. os.replace() per rename atomico (sostituisce file vecchio)

UTILITÀ: Evita corruzione del file JSON se il processo viene killato durante
         la scrittura.


┌─────────────────────────────────────────────────────────────────────────────┐
│ next_session_filename(prefix="session")                                     │
└─────────────────────────────────────────────────────────────────────────────┘

FUNZIONE: Genera nome file univoco basato su timestamp.

FORMATO: {prefix}_YYYY_MM_DD__HH_MM_SS.json


CONCETTI TECNICI CHIAVE
================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pseudo-Terminal (PTY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Un PTY è una coppia master/slave che simula un terminale reale:
- Il processo eseguito vede lo slave come un terminale normale
- Il master può essere usato per leggere output e scrivere input
- Questo permette di catturare I/O anche per programmi che richiedono TTY
  (es. programmi che usano ncurses, o che controllano il terminale)

VANTAGGI:
- I programmi si comportano come in un terminale reale
- Possibilità di controllare attributi terminale (es. ECHO)
- Cattura accurata di output anche per programmi interattivi complessi


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
select() per I/O Multiplexing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

select.select() permette di monitorare più file descriptor simultaneamente:
- Blocca fino a quando almeno uno è pronto per I/O
- Ritorna liste di FD pronti per lettura/scrittura/eccezioni
- Evita busy-waiting e permette gestione reattiva di input/output

Nel progetto:
- Monitora master (output processo) e stdin (input utente)
- Quando uno è pronto, lo gestisce senza bloccare l'altro
- Permette output immediato anche mentre l'utente digita


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Buffering Output
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEMA: Senza setvbuf/fflush, output senza newline può rimanere nel buffer
          della libc e non apparire immediatamente.

SOLUZIONE 1 (stdbuf):
- Se disponibile, avvolge il binario con stdbuf -o0 -e0
- Forza stdout/stderr non bufferizzati a livello di sistema
- Output appare immediatamente anche senza newline

SOLUZIONE 2 (PTY):
- I PTY sono tipicamente line-buffered di default
- Output viene flushato quando il programma legge da stdin
- Comportamento più naturale per programmi interattivi


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Coalescing Output per GDB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PROBLEMA: Comandi gdb come "disas main" producono molte righe di output che
          vengono lette in chunk da 4096 byte, creando molte entry nel log.

SOLUZIONE:
- Accumula output in un buffer (bytearray)
- Flush del buffer solo quando:
  a) L'utente invia input (boundary naturale tra comandi)
  b) Il processo termina (output residuo)
- Ogni "burst" di output diventa una singola entry nel log JSON
- Migliora leggibilità e gestione del log


FLUSSO DI ESECUZIONE COMPLETO
================================================================================

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMANDO: python3 harness.py run <binario>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. harness.py parsea argomenti → chiama run_and_record(binary_path)

2. run_and_record():
   a) Crea SessionLogger
   b) Risolve path binario
   c) Valida esistenza/eseguibilità
   d) Costruisce comando (con stdbuf se disponibile)
   e) Chiama _interactive_pty_session()

3. _interactive_pty_session():
   a) Crea PTY (master/slave)
   b) Disabilita ECHO su slave
   c) Avvia processo con stdin/stdout/stderr → slave
   d) Loop select():
      - Se output disponibile → legge, stampa, accumula in buffer
      - Se input utente → flush buffer, scrive su master, registra input
   e) Al termine → flush buffer residuo, finalizza sessione

4. Salvataggio log JSON in sessions/


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMANDO: python3 harness.py gdb <binario>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. harness.py → chiama gdb_and_record(binary_path)

2. gdb_and_record():
   a) Crea SessionLogger con metadata={"wrapper": "gdb"}
   b) Risolve e valida binario
   c) Costruisce comando: ["gdb", "-q", "-ex", "set pagination off", "--args", binary]
   d) Chiama _interactive_pty_session() con questo comando

3. _interactive_pty_session() esegue come sopra, ma:
   - Il processo è gdb invece del binario diretto
   - L'output include sia prompt/comandi gdb che output del programma debugato
   - Tutto viene catturato e registrato insieme

4. Salvataggio log JSON (con "args" che contiene comando gdb completo)


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMANDO: python3 harness.py replay <logfile.json>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. harness.py → chiama replay_session(log_filename)

2. replay_session():
   a) Carica e parsea JSON
   b) Estrae "target" e "args" (se presente)
   c) Costruisce comando:
      - Se "args" presente → usa quello (per sessioni gdb)
      - Altrimenti → risolve "target" e aggiunge stdbuf se disponibile
   d) Crea PTY e avvia processo
   e) Legge output iniziale (con timeout)
   f) Per ogni input nel log:
      - Stampa messaggio indicativo
      - Scrive input su master
      - Legge output risultante (con timeout tra chunk)
   g) Attende terminazione processo
   h) Drena output residuo
   i) Stampa codice di uscita


CASI D'USO E SCENARI
================================================================================

SCENARIO 1: Esecuzione semplice di un binario interattivo
- Utente esegue: harness.py run binaries/vault
- Il binario viene eseguito con stdbuf per output immediato
- L'utente interagisce normalmente
- Tutto viene registrato in un JSON

SCENARIO 2: Debug con gdb
- Utente esegue: harness.py gdb binaries/ctf
- GDB si avvia e l'utente può usare comandi gdb
- Output di gdb E del programma vengono catturati insieme
- La sessione può essere riprodotta con replay

SCENARIO 3: Replay di una sessione
- Utente esegue: harness.py replay sessions/session_2026_02_18__17_00_00.json
- Il sistema ricostruisce il comando originale (incluso gdb se era una sessione gdb)
- Reinvia gli input registrati
- Mostra l'output risultante (può differire leggermente per timing, ma struttura simile)


LIMITAZIONI E CONSIDERAZIONI
================================================================================

1. TIMING: Il replay non replica esattamente i timing originali (usa timeout
   fissi), quindi output può apparire leggermente diverso.

2. STATO: Il replay assume che il binario sia nello stesso stato iniziale
   (non gestisce stato persistente tra esecuzioni).

3. INTERATTIVITÀ: Durante il replay, l'utente vede l'output ma non può
   interagire (gli input vengono presi dal log).

4. PTY: Richiede supporto PTY (disponibile su Linux/Unix, non Windows nativo).

5. STDBUF: Opzionale ma consigliato per output immediato senza modifiche
   al codice sorgente del binario.


CONCLUSIONI
================================================================================

Il progetto ReBin fornisce un sistema completo per:
- Eseguire binari in modo interattivo con cattura completa I/O
- Registrare sessioni in formato JSON strutturato
- Riprodurre sessioni per analisi o testing

L'uso di PTY garantisce compatibilità con programmi che richiedono terminale,
mentre il buffering intelligente e il supporto per wrapper (gdb) rendono il
tool adatto sia per uso semplice che per debugging avanzato.
