#include <stdio.h>
#include <stdlibi.h>
#include <unistd.h>

int main() {
    int secret = 0xdeadbeef;
    char name[100] = {0};
	printf("Ciao\n");
	while(1){
    read(0, name, 0x100);
    if (secret == 0x41414141) {
        puts("Wow! Here's a secret.");
		return 0;
	}
    puts("I guess you're not cool enough to see my secret");
	}
}
