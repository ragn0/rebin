#include <stdio.h>
#include <unistd.h>

int main() {
    // Variabili memorizzate una dopo l'altra nello stack
    char pincode[16];
    int premium_access = 0; // Inizialmente, l'accesso è negato (0 = false)

    // Disabilita il buffering per il tuo tool
    setvbuf(stdout, NULL, _IONBF, 0);
    
    printf("Vault 713 - Inserire codice di sblocco: ");

    // La vulnerabilità è qui. `gets` non controlla la lunghezza
    // e scriverà oltre i 16 byte del buffer `pincode`.
    gets(pincode);

    // Controlla se la variabile `premium_access` è stata modificata
    while (premium_access == 0) {
        printf("\n[!] Codice non valido. Accesso negato.\n");
        gets(pincode);
	}
    printf("\n[+] Accesso Premium Sbloccato! Benvenuto.\n");
    return 0;
}
