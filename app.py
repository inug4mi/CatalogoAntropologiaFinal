# Lab 4 – Mecanismos de Sincronización
**Sistemas Operativos – Universidad de Antioquia**

---

## Estructura del proyecto

| Archivo | Tarea | Mecanismos usados |
|---------|-------|-------------------|
| `queue.c` | Cola thread-safe | mutex + 2 condvars (`hay_datos` / `hay_espacio`) + timedwait |
| `producer_consumer.c` | Productor-Consumidor | semáforos `libres`/`listos` + 2 mutexes separados |
| `dining_philosophers.c` | Filósofos Comensales | mutex/tenedor + semáforo `sala` + jerarquía de recursos |

Todos los archivos incluyen **métricas en tiempo de ejecución**: tiempos de espera por hilo (promedio, mínimo, máximo), nivel del buffer y throughput.

---

## Compilar y ejecutar

```bash
gcc -Wall -o queue               queue.c               -lpthread
gcc -Wall -o producer_consumer   producer_consumer.c   -lpthread
gcc -Wall -o dining_philosophers dining_philosophers.c  -lpthread

./queue
./producer_consumer
./dining_philosophers
```

---

## Tarea 1 – Cola Thread-Safe (`queue.c`)

### Decisiones de diseño

Se usaron **dos variables de condición** con nombres descriptivos en español:
- `hay_datos`: el productor señaliza acá cuando mete un item → despierta consumidores.
- `hay_espacio`: el consumidor señaliza acá cuando saca un item → despierta productores.

Para que los consumidores puedan detectar que la producción terminó sin quedarse bloqueados eternamente, `sacar()` usa `pthread_cond_timedwait` con un timeout de 100 ms en vez del `wait` clásico. Cuando expira el timeout, el hilo revisa el flag `produccion_terminada` y sale limpiamente si la cola está vacía.

```
Flujo productor:
  meter(item) → lock → [wait si lleno] → escribir → signal(hay_datos) → unlock

Flujo consumidor:
  sacar() → lock → [timedwait si vacío] → leer → signal(hay_espacio) → unlock
```

### Métricas que se miden
- Items procesados por hilo
- Tiempo de espera promedio, mínimo y máximo
- Throughput global (items/segundo)

---

## Tarea 2 – Productor-Consumidor (`producer_consumer.c`)

### Decisiones de diseño

Se usan **4 semáforos** en total:
- `libres` (init = TAM_BUFFER): cuenta los slots vacíos disponibles.
- `listos` (init = 0): cuenta los items listos pa' consumir.
- `mu_prod` como mutex de productores (via `pthread_mutex_t`).
- `mu_cons` como mutex de consumidores (via `pthread_mutex_t`).

La diferencia clave frente a la solución clásica de un mutex global: **los productores y consumidores tienen mutexes independientes**. Eso significa que un productor escribiendo y un consumidor leyendo *pueden operar en paralelo* siempre que no estén en el mismo slot, lo que en la práctica reduce la contención cuando el buffer está parcialmente lleno.

```
Productor:  usleep → sem_wait(libres) → lock(mu_prod) → escribir → unlock → sem_post(listos)
Consumidor: sem_wait(listos) → lock(mu_cons) → leer → unlock → sem_post(libres) → usleep
```

### Métricas que se miden
- Tiempo de espera en semáforos
- Nivel del buffer al momento de cada operación (min/max/promedio)
- Throughput global

---

## Tarea 3 – Filósofos Comensales (`dining_philosophers.c`)

### Decisiones de diseño

Se combinan dos técnicas para eliminar deadlock:

**1. Jerarquía de recursos (orden de adquisición):**
Cada filósofo siempre agarra primero el tenedor de menor índice entre los dos que necesita. El filósofo 4, que normalmente agarraría [4, 0], acá agarra [0, 4] — esto rompe la espera circular.

```c
int primero = izq < der ? izq : der;  // menor índice primero
int segundo = izq < der ? der : izq;
```

**2. Semáforo de sala (N-1 comensales):**
El semáforo `sala` inicializado en `N-1` garantiza que máximo 4 de los 5 filósofos intenten comer simultáneamente. Esto asegura que siempre haya al menos un par de tenedores libres para que alguien pueda progresar.

### Métricas que se miden
- Tiempo de espera pa' obtener tenedores (contención real)
- Tiempo comiendo y pensando
- Brecha máxima entre comidas consecutivas (indicador de inanición potencial)
- **Índice de Fairness de Jain**: mide qué tan equitativamente se repartieron las comidas entre filósofos. Un valor de 1.0 significa distribución perfecta.

```
Índice Jain = (Σxi)² / (n · Σxi²)    rango: [1/n, 1.0]
```

---

## Notas generales

- Todos los tiempos de espera se miden con `CLOCK_MONOTONIC` para evitar saltos por sincronización NTP.
- Los `usleep` simulan trabajo real; en producción se eliminarían.
- Los nombres de variables están en español para mayor claridad en el contexto del curso.
