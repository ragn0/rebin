#include <stdio.h>
#include <string.h>
#include <stdlib.h> // Per exit()
#include <unistd.h> // Per sleep()

// Funzione vulnerabile a Buffer Overflow
void echo_function() {
    char buffer[64]; // Buffer di 64 byte
    printf("Inserisci il tuo messaggio (max 63 caratteri per sicurezza): ");
    fflush(stdout); // Forza lo svuotamento del buffer di output

    // Legge fino a 200 caratteri, causando un overflow se l'input è > 63
    ssize_t bytes_read = read(STDIN_FILENO, buffer, 200); 
    if (bytes_read > 0) {
        buffer[bytes_read - 1] = 0; // Termina la stringa correttamente (rimuovi il newline)
        printf("Hai scritto: %s\n", buffer);
    }
}

// Funzione vulnerabile a Format String
void debug_function(char *input) {
    char name[32];
    strncpy(name, "User", sizeof(name) - 1); // Nome predefinito
    name[sizeof(name) - 1] = '\0';

    printf("Messaggio di debug per %s: ", name);
    printf(input); // La vulnerabilità è qui: printf con input non controllato
    printf("\n");
}

int main() {
    setvbuf(stdout, NULL, _IONBF, 0); // Disabilita il buffering dell'output
    setvbuf(stdin, NULL, _IONBF, 0);  // Disabilita il buffering dell'input

    char choice[16];

    while (1) {
        printf("\nScegli un'opzione:\n");
        printf("1. Echo Message (Buffer Overflow test)\n");
        printf("2. Debug Info (Format String test)\n");
        printf("3. Exit\n");
        printf("> ");
        fflush(stdout);

        if (fgets(choice, sizeof(choice), stdin) == NULL) {
            printf("\nErrore di input o EOF.\n");
            break;
        }
        choice[strcspn(choice, "\n")] = 0; // Rimuovi il newline

        if (strcmp(choice, "1") == 0) {
            echo_function();
        } else if (strcmp(choice, "2") == 0) {
            char debug_input[100];
            printf("Inserisci la stringa di formato: ");
            fflush(stdout);
            if (fgets(debug_input, sizeof(debug_input), stdin) == NULL) {
                break;
            }
            debug_input[strcspn(debug_input, "\n")] = 0;
            debug_function(debug_input);
        } else if (strcmp(choice, "3") == 0) {
            printf("Arrivederci!\n");
            break;
        } else {
            printf("Scelta non valida. Riprova.\n");
        }
        sleep(0.5); // Breve pausa per evitare che l'output si confonda troppo velocemente
    }

    return 0;
}