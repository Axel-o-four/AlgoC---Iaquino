# Progetto di Elementi di Ingegneria dei Linguaggi di Programmazione
**Sabato Iaquino (Matricola 0512123029) a.a. 2025/2026**
**Corso di Elementi di Ingegneria dei Linguaggi di Programmazione tenuto dal Professore Gennaro Costagliola**

# AlgoC - Algorythms in C

### Cos'è AlgoC?

AlgoC è un **linguaggio di programmazione** per la scrittura rapida degli algoritmi con la **sintassi degli pseudocodici**: la maggior parte degli algoritmi, anche quelli presentati ai corsi universitari, vengono rappresentati tramite pseudocodice, questo richiede un passaggio di traduzione affinché siano effettivamente compilabili. Con AlgoC è possibile scrivere algoritmi in pseudocodice **compilabili direttamente in C**, senza necessità di traduzione. AlgoC ha un **compilatore completo**, in Python, che traduce algoritmi scritti in pseudocodice direttamente in codice **C eseguibile**. 

L'obiettivo è eliminare il gap tra la rappresentazione teorica degli algoritmi e la loro implementazione pratica, permettendo di scrivere algoritmi con sintassi pseudocodicale senza necessità di traduzione manuale.

---

### Caratteristiche principali

- **Compilazione automatica**: dal codice algoc si genera C ottimizzato e eseguibile.
- **Data type supportati**: i data type supportati sono `int`, `real`, `string` e `boolean`.
- **Data structures supportate**: strutture di supporto alla progettazione di algoritmi, come `list`, `stack`, `queue`, `tree` e `graph`, con le rispettive funzioni vengono aggiunte dalla libreria di supporto `algoc.h`.
- **Strutture di controllo semplificate**: le strutture di controllo vengono ottimizzate per l'iterazione sugli elementi di una struttura dati.
- **Assegnazione semplificata**: l'assegnazione viene svolta tramite l'operatore `<-`.
- **Operatori semplificati**: viene rimosso il supporto agli operatori bitwise, di poca utilità in questo campo, e viene semplificato l'uso degli operatori, divisi in:
  - **Aritmetici**: `+`,`-`,`*`,`/` e `%`.
  - **Relazionali**: `<`, `>`, `<=`, `>=` e `=`.
  - **Logici**: `|`, `&` e `!`.
- **Passaggi commentabili**: è possibile aggiungere commenti in ogni punto del codice racchiudendo il testo tra `%`.

### Struttura di progetto

AlgoC/
├── README.md                           # Questo file
├── src/
│   └── grammar.lark                    # Grammatica in EBNF per Lark
└── Documentazione/
    └── ~~ Documentazione grammatica.pdf   # Documentazione della grammatica di AlgoC ~~