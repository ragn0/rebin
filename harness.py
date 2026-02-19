import argparse
from pwn import context
import os
from lib.run import gdb_and_record, run_and_record
from lib.replay import replay_session
# Rende l'output di pwntools meno verboso
context.log_level = "error"

if __name__ == "__main__":
    # Gestione dei comandi da riga di comando
    parser = argparse.ArgumentParser(description="Harness per interagire, registrare e rigiocare sessioni con binari.")
    subparsers = parser.add_subparsers(dest='command', required=True, help='Scegli il comando da eseguire')

    # Comando 'run' per interagire e registrare
    parser_run = subparsers.add_parser('run', help='Avvia una sessione interattiva e la registra.')
    parser_run.add_argument('binary', help='Path del binario da eseguire.')

    # Comando 'gdb' per interagire e registrare tramite gdb
    parser_gdb = subparsers.add_parser('gdb', help='Avvia gdb su un binario e registra la sessione (I/O di gdb + programma).')
    parser_gdb.add_argument('binary', help='Path del binario da eseguire sotto gdb.')

    # Comando 'replay' per rigiocare una sessione
    parser_replay = subparsers.add_parser('replay', help='Riproduce una sessione da un file di log.')
    parser_replay.add_argument('logfile', help='Path del file di log JSON da rigiocare.')
    
    args = parser.parse_args()

    # Esegui il comando scelto
    if args.command == 'run':
        run_and_record(args.binary)

    elif args.command == 'gdb':
        gdb_and_record(args.binary)

    elif args.command == 'replay':
        replay_session(args.logfile)
